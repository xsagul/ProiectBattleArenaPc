"""What is each packet id of the 16.20 replay? One block per id, from the packets themselves read by the
client's own readers (server/packet_emu16.py), fields in clear:

    python tools/digest16.py [samples per id, default 250]   -> data/exe1620/digest.txt

Per id: how many, first / last time, per record kind, body sizes, whose net id the packet is about
(0, a champion, another unit), and for every field of the object: size, how many distinct values, whether
the values are net ids of units of the match, a few values (as number and as float), and the texts found.
Names are not in the client: a packet is recognised from this, as on 13.3 (kind_strings / handler digest).
"""
import collections, os, statistics, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
import packet_emu16 as P   # noqa: E402
import rofl2               # noqa: E402


def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    r = rofl2.Rofl2(P.ROFL)
    count, first, last, sizes, about = collections.Counter(), {}, {}, collections.defaultdict(list), collections.defaultdict(collections.Counter)
    samples = collections.defaultdict(list)
    heroes = set()
    kinds = collections.defaultdict(collections.Counter)
    for e, (t, ch, pid, obj, body) in rofl2.stream(r, (3, 2, 1)):
        if e["type"] != 1 and e["id"] != 1:
            continue                          # later keyframes repeat the state: only the first one
        kinds[pid][{1: "stream", 2: "start", 3: "info"}[e["type"]]] += 1
        count[pid] += 1
        first.setdefault(pid, t)
        last[pid] = t
        if len(sizes[pid]) < 5000:
            sizes[pid].append(len(body))
        about[pid][obj] += 1
        if pid == 222:
            heroes.add(obj)
        n = count[pid]
        if n <= per // 2 or (n % 97 == 0 and len(samples[pid]) < per):   # the first ones, then a thin spread
            samples[pid].append((t, obj, body))
    table = P.table()
    emu = P.Emu()
    units = set()
    for pid in about:
        units |= {o for o in about[pid] if o}
    out = open(os.path.join(ROOT, "data", "exe1620", "digest.txt"), "w", encoding="utf-8")
    for pid in sorted(count):
        info = table.get(pid)
        ab = about[pid]
        who = f"net id 0: {ab[0]}" if ab[0] else ""
        nh = sum(v for o, v in ab.items() if o in heroes)
        who += f"  champions: {nh}" if nh else ""
        other = sum(v for o, v in ab.items() if o and o not in heroes)
        who += f"  other units: {other} ({len([o for o in ab if o and o not in heroes])} distinct)" if other else ""
        sz = sizes[pid]
        out.write(f"\n=== {pid}: {count[pid]} packets ({dict(kinds[pid])}), t {first[pid]:.2f}..{last[pid]:.2f}, body {min(sz)}..{max(sz)} B "
                  f"(median {statistics.median(sz):.0f}), object {info['size'] if info else '?'} B\n    about: {who}\n")
        if not info:
            continue
        fields = collections.defaultdict(list)       # (block label, offset, size) -> values
        texts = collections.Counter()
        for t, obj, body in samples[pid]:
            tr = {}
            ok, left, o = emu.deserialize(info, pid, obj, body, tr)
            if ok != 1 or left:
                continue
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
    print(len(count), "packet kinds written")


if __name__ == "__main__":
    main()
