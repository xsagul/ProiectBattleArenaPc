"""What is each packet id of a recorded LIVE 16.20 match? The live counterpart of digest16.py: one block per id,
fields in clear through the client's own readers (server/packet_emu16.py), plus what only a live recording can say:
in which part of the match the id is sent (answer to the first packets / start state / match), on which channel,
which client packet it answers (pairs.txt), and which kind of unit it is about (a unit's kind = the id of the
first packet that named it, e.g. a champion is first named by its creation packet).

    python tools/live_digest16.py data/live/<gameId> [samples per id, default 200]  -> <gameId>/digest.txt
"""
import collections, os, re, statistics, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
import live16               # noqa: E402
import packet_emu16 as P    # noqa: E402
import roles16              # noqa: E402

PART = {0: "info", 1: "start", 2: "match"}


def role_names():
    out = {}
    for k, v in vars(roles16).items():
        if k.isupper() and isinstance(v, int):
            out.setdefault(v, k)
    return out


def main():
    game = sys.argv[1]
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    cap = live16.Capture(game)
    names = role_names()
    count, first, last = collections.Counter(), {}, {}
    sizes, chans = collections.defaultdict(list), collections.defaultdict(collections.Counter)
    parts = collections.defaultdict(collections.Counter)
    about = collections.defaultdict(collections.Counter)
    born = {}                                     # net id -> id of the first packet about it
    samples = collections.defaultdict(list)
    c2s = collections.Counter()
    c2s_info = {}
    for t, way, ch, pid, net, body in live16.rows(cap.path):
        if way == "C2S":
            c2s[pid] += 1
            c2s_info.setdefault(pid, (t, ch, collections.Counter()))[2][len(body)] += 1
            continue
        part = 0 if t < cap.gates[1] else 1 if t < cap.gates[2] else 2
        count[pid] += 1
        first.setdefault(pid, t)
        last[pid] = t
        if len(sizes[pid]) < 5000:
            sizes[pid].append(len(body))
        chans[pid][ch] += 1
        parts[pid][PART[part]] += 1
        about[pid][net] += 1
        if net:
            born.setdefault(net, pid)
        n = count[pid]
        if n <= per // 2 or (n % 97 == 0 and len(samples[pid]) < per):
            samples[pid].append((t, net, body))
    heroes = {u for u, p in born.items() if p == roles16.HERO_CREATE}
    kinds = collections.Counter(born.values())
    pairs = {}
    pp = os.path.join(game, "pairs.txt")
    if os.path.exists(pp):
        cur = None
        for line in open(pp, encoding="utf-8"):
            m = re.match(r"^(\d+)( [A-Z_0-9]+)?: (\d+) times", line)
            if m:
                cur = int(m.group(1))
                continue
            m = re.match(r"^\s+-> (\d+)", line)
            if m and cur is not None:
                pairs.setdefault(int(m.group(1)), []).append(f"{cur}: {line.strip()[3:]}")
    codec = os.path.join(ROOT, "data", "exe1620", "codec")
    table = P.table()
    emu = P.Emu()
    out = open(os.path.join(game, "digest.txt"), "w", encoding="utf-8")
    out.write(f"live match {cap.name}: parts begin at {['%.3f' % g for g in cap.gates]} s; {sum(count.values())} server packets, "
              f"{len(count)} ids; {sum(c2s.values())} client packets, {len(c2s)} ids\n")
    out.write("units by the packet that first named them: " +
              ", ".join(f"{names.get(p, p)} {n}" for p, n in kinds.most_common()) + "\n")
    out.write("\n--- client packets\n")
    for pid in sorted(c2s, key=lambda p: -c2s[p]):
        t, ch, sz = c2s_info[pid]
        out.write(f"  {pid:5} {names.get(pid, ''):16} x{c2s[pid]:6}  first {t:8.2f} s  channel {ch}  sizes {dict(sz.most_common(4))}\n")
    for pid in sorted(count):
        info = table.get(pid)
        ab = about[pid]
        who = []
        if ab[0]:
            who.append(f"net id 0: {ab[0]}")
        nh = sum(v for o, v in ab.items() if o in heroes)
        if nh:
            who.append(f"champions {nh} ({len([o for o in ab if o in heroes])} distinct)")
        other = collections.Counter()
        for o, v in ab.items():
            if o and o not in heroes:
                other[names.get(born.get(o), born.get(o))] += v
        if other:
            who.append("other units by birth packet: " + ", ".join(f"{k} {v}" for k, v in other.most_common(5)))
        sz = sizes[pid]
        dur = max(last[pid] - first[pid], 1e-6)
        out.write(f"\n=== {pid} {names.get(pid, '')}: {count[pid]} packets {dict(parts[pid])}, channel {dict(chans[pid])}, "
                  f"t {first[pid]:.2f}..{last[pid]:.2f} ({count[pid] / dur:.2f}/s), body {min(sz)}..{max(sz)} B "
                  f"(median {statistics.median(sz):.0f}), object {info['size'] if info else '?'} B, "
                  f"codec {'yes' if os.path.exists(os.path.join(codec, f'{pid}.tree.json')) else 'NO'}\n")
        out.write(f"    about: {'; '.join(who)}\n")
        for p in pairs.get(pid, []):
            out.write(f"    answers {p}\n")
        if not info:
            continue
        fields = collections.defaultdict(list)
        texts = collections.Counter()
        read = collections.Counter()
        for t, obj, body in samples[pid]:
            tr = {}
            try:
                ok, left, o = emu.deserialize(info, pid, obj, body, tr)
            except Exception as e:
                read["error " + type(e).__name__] += 1
                continue
            if ok != 1 or left:
                read["not exact"] += 1
                continue
            read["exact"] += 1
            for bi, (label, flds) in enumerate(P.decoded_blocks(emu, tr)):
                if bi > 0:
                    raw = b"".join(f[1] for f in flds)
                    if 2 <= len(raw) <= 80 and all(32 <= c < 127 for c in raw.rstrip(b"\0")) and raw.rstrip(b"\0"):
                        texts[raw.rstrip(b"\0").decode()] += 1
                        continue
                for off, raw, hidden, w in P.meaningful(flds):
                    if bi == 0 and off < 0x10:
                        continue
                    fields[(min(bi, 1), off, len(raw))].append(raw)
            emu.heap = P.HEAP + 0x1000
        out.write(f"    read by the client's reader: {dict(read)}\n")
        units = set(born)
        for (bi, off, n), vals in sorted(fields.items()):
            distinct = collections.Counter(vals)
            line = f"    {'obj' if bi == 0 else 'blk'} +{off:#05x} {n:3} B  in {len(vals):3} of {len(samples[pid])}, {len(distinct):3} distinct"
            if n == 4:
                ints = [struct.unpack('<I', v)[0] for v in vals]
                ids = sum(1 for v in ints if v in units)
                if ids > len(ints) * 0.6:
                    line += f"  NET IDS ({sum(1 for v in ints if v in heroes)} champions)"
                else:
                    fl = [struct.unpack('<f', v)[0] for v in vals]
                    if all(abs(x) < 1e7 and (abs(x) > 1e-4 or x == 0) for x in fl) and any(x != int(x) for x in fl):
                        line += f"  floats {min(fl):.3f}..{max(fl):.3f}"
                    else:
                        line += f"  ints {min(ints)}..{max(ints)}"
            elif n in (1, 2, 8):
                ints = [int.from_bytes(v, 'little') for v in vals]
                line += f"  ints {min(ints)}..{max(ints)}"
                if n == 8:
                    d = [struct.unpack('<d', v)[0] for v in vals]
                    if all(abs(x) < 1e9 for x in d):
                        line += f"  doubles {min(d):.3f}..{max(d):.3f}"
            elif n == 12:
                v3 = [struct.unpack('<fff', v) for v in vals]
                line += f"  vec3 e.g. ({v3[0][0]:.0f}, {v3[0][1]:.0f}, {v3[0][2]:.0f})"
            line += "   e.g. " + " ".join(v.hex() if len(v) <= 8 else v[:8].hex() + ".." for v, c in distinct.most_common(4))
            out.write(line + "\n")
        if texts:
            out.write("    texts: " + ", ".join(f"{t!r} x{c}" for t, c in texts.most_common(14)) + "\n")
        out.flush()
    out.close()
    print(len(count), "server ids,", len(c2s), "client ids ->", os.path.join(game, "digest.txt"))


if __name__ == "__main__":
    main()
