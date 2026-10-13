"""What does the real server answer to each thing the client sends? From a decoded live match
(tools/live_decode.py -> data/live/<gameId>/packets.tsv):

    python tools/live_pairs.py data/live/<gameId> [--window 0.25] [--head 70]   -> <gameId>/pairs.txt

1. the opening: client packets in order, the server's bursts between them
2. per client packet id: how often, on which channel, and the server ids that follow it far more often
   than they appear in any window of the same length (share of requests followed, how many times the
   chance rate, typical delay, whether the reply is about the same net id, whether it repeats bytes
   of the request)
3. per server packet id: how often, cadence, and whether it is somebody's reply or the server's own

Names come from server/roles16.py where an id has one; everything else stays a number.
A statistic, not a proof: a pair found here is where to look, the fields say what it is.
"""
import bisect, collections, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))


def names():
    try:
        import roles16
        return {v: k for k, v in vars(roles16).items() if k.isupper() and isinstance(v, int)}
    except Exception:
        return {}


def lcs(a, b):
    """Length of the longest run of bytes found in both."""
    best = 0
    for i in range(len(a)):
        for n in range(best + 1, len(a) - i + 1):
            if a[i:i + n] in b:
                best = n
            else:
                break
    return best


def main():
    args = sys.argv[1:]
    opt = lambda k, d: type(d)(args[args.index(k) + 1]) if k in args else d
    game, W, head = args[0], opt("--window", 0.25), opt("--head", 70)
    nm = names()
    tag = lambda pid: f"{pid} {nm[pid]}" if pid in nm else str(pid)
    rows = []
    for line in open(os.path.join(game, "packets.tsv"), encoding="utf-8"):
        t, way, ch, fl, ex, pid, net, n, body = line.rstrip("\n").split("\t")
        rows.append((float(t), way, int(ch), int(pid), int(net, 16), bytes.fromhex(body)))
    span = rows[-1][0] - rows[0][0]
    c2s = collections.defaultdict(list)
    s2c = collections.defaultdict(list)
    for r in rows:
        (c2s if r[1] == "C2S" else s2c)[r[3]].append(r)
    s_times = {pid: [r[0] for r in v] for pid, v in s2c.items()}
    steady = {pid for pid, v in c2s.items() if len(v) >= span / 3}      # at least one per 3 s: pings and the like
    out = open(os.path.join(game, "pairs.txt"), "w", encoding="utf-8")

    def say(s=""):
        print(s)
        out.write(s + "\n")

    say(f"match {os.path.basename(os.path.normpath(game))}: {span:.0f} s, C2S {sum(map(len, c2s.values()))} packets / {len(c2s)} ids, "
        f"S2C {sum(map(len, s2c.values()))} packets / {len(s2c)} ids, window {W} s")

    say("\n--- 1. the opening (steady client packets left out: " + ", ".join(tag(p) for p in sorted(steady)) + ")")
    burst, shown = None, 0
    def flush():
        nonlocal burst, shown
        if burst:
            t0, t1, c, nb = burst
            say(f"   {t0:9.3f} S2C {sum(c.values()):5} packets {nb:6} B in {t1 - t0:5.3f} s: "
                + " ".join(f"{tag(k)}x{v}" if v > 1 else tag(k) for k, v in c.most_common(14)) + (" ..." if len(c) > 14 else ""))
            shown += 1
        burst = None
    for t, way, ch, pid, net, body in rows:
        if shown >= head:
            break
        if way == "C2S":
            if pid in steady:
                continue
            flush()
            say(f"{t:9.3f} C2S ch {ch} {tag(pid)} about {net:08x} {len(body)} B: {body[:20].hex()}")
            shown += 1
        else:
            if burst and t - burst[1] > 0.5:
                flush()
            if not burst:
                burst = [t, t, collections.Counter(), 0]
            burst[1] = t
            burst[2][pid] += 1
            burst[3] += len(body)
    flush()

    # chance rate of each server id: the share of windows of length W (every W/2) that hold it
    grid = max(1, int(span / (W / 2)))
    base = {}
    for pid, ts in s_times.items():
        hit, k = 0, 0
        for i in range(grid):
            a = rows[0][0] + i * W / 2
            k = bisect.bisect_left(ts, a)
            hit += k < len(ts) and ts[k] <= a + W
        base[pid] = hit / grid

    say(f"\n--- 2. client packets and what follows them within {W} s")
    reply_of = collections.defaultdict(list)
    for pid in sorted(c2s, key=lambda p: -len(c2s[p])):
        v = c2s[pid]
        gaps = [b[0] - a[0] for a, b in zip(v, v[1:])]
        chans = sorted({r[2] for r in v})
        about = "no unit" if all(r[4] == 0 for r in v) else f"{len({r[4] for r in v})} unit(s)"
        say(f"{tag(pid)}: {len(v)} times, channel {chans}, {min(len(r[5]) for r in v)}..{max(len(r[5]) for r in v)} B, about {about}"
            + (f", every {statistics.median(gaps):.2f} s (median)" if gaps else ""))
        found = []
        for y, ts in s_times.items():
            delays, same_net, runs = [], 0, []
            for t, _, _, _, net, body in v:
                k = bisect.bisect_left(ts, t)
                if k < len(ts) and ts[k] <= t + W:
                    delays.append(ts[k] - t)
                    r = s2c[y][k]
                    same_net += net != 0 and r[4] == net
                    if len(runs) < 25 and body:
                        runs.append(lcs(body, r[5]))
            share = len(delays) / len(v)
            lift = share / base[y] if base[y] else float("inf")
            if len(delays) >= 2 and ((share >= 0.5 and lift >= 3) or (share >= 0.9 and lift >= 1.5)):
                found.append((share * min(lift, 50), y, share, lift, statistics.median(delays), same_net / len(delays),
                              statistics.median(runs) if runs else 0))
        for _, y, share, lift, delay, same, run in sorted(found, reverse=True)[:8]:
            reply_of[y].append(pid)
            say(f"     -> {tag(y)}: after {100 * share:.0f} % of them, {lift:.1f} x chance, {1000 * delay:.0f} ms later"
                + (f", same unit {100 * same:.0f} %" if same else "") + (f", repeats {run:.0f} bytes of the request" if run >= 4 else ""))
        if not found:
            say("     -> nothing stands out")

    say("\n--- 3. server packets")
    for pid in sorted(s2c, key=lambda p: -len(s2c[p])):
        v = s2c[pid]
        gaps = [b[0] - a[0] for a, b in zip(v, v[1:])]
        chans = sorted({r[2] for r in v})
        units = len({r[4] for r in v if r[4]})
        say(f"{tag(pid)}: {len(v)} times, channel {chans}, {min(len(r[5]) for r in v)}..{max(len(r[5]) for r in v)} B, "
            f"{'about %d unit(s)' % units if units else 'about no unit'}, first {v[0][0]:.1f} s last {v[-1][0]:.1f} s"
            + (f", median gap {statistics.median(gaps):.2f} s" if gaps else "")
            + (f"  <- reply to {', '.join(tag(p) for p in reply_of[pid])}" if pid in reply_of else ""))
    out.close()


if __name__ == "__main__":
    main()
