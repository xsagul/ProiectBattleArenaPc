"""Which 16.20 packet id is which 13.3 packet id? Compared by the learnt formats (data/exe133/codec and
data/exe1620/codec, *.tree.json): the fields of a packet in the order its reader reads them, each as
kind + size (number of 1 / 2 / 4 / 8 / 12 bytes, varint, text, list, embedded struct), recursively.
Header bit positions are different on every patch and are ignored.

    python tools/match_ids.py            -> data/exe1620/id_map.txt  (+ id_map.json)

A match is only as good as its line says:
  unique      one 13.3 id and one 16.20 id have this exact shape
  by count    several ids share the shape; paired by how often they occur in each replay (weak: the two
              replays are different matches on different patches)
  near        no exact shape; the closest one (fields added or removed), with the distance
New mechanics have no counterpart and old packets may be gone: unmatched ids are listed, not forced.
"""
import collections, difflib, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))


def field_sig(f, structs, depth=0):
    """kind + size of a field, plus the values it takes in its constant modes (defaults: they belong to the
    packet's meaning, not to the patch)"""
    consts = sorted({d["value"] for d in f["modes"].values() if d["kind"] == "const" and isinstance(d.get("value"), str)})
    cs = "{" + ",".join(c.rstrip("0") or "0" for c in consts) + "}" if consts else ""
    kinds = [d for d in f["modes"].values() if d["kind"] not in ("const", "invalid", "unknown")]
    if not kinds:
        return f"c{f['size']}{cs}"
    d = kinds[0]
    k = d["kind"]
    if k == "fixed":
        return f"n{f['size']}{cs}"
    if k == "varint":
        return "v" + cs
    if k == "text":
        return "T"
    if k == "struct":
        return "S(" + struct_sig(structs.get(d["type"]), structs, depth + 1) + ")"
    if k == "seq":
        el = d.get("elem") or {}
        if el.get("kind") == "struct":
            return "L(" + struct_sig(structs.get(el["type"]), structs, depth + 1) + ")"
        return "L" + {"varint": "v", "text": "T"}.get(el.get("kind"), "?")
    return "?"


def struct_sig(st, structs, depth=0):
    """fields in the order they lie in the object (the class as declared), not in reading order"""
    if st is None or depth > 6:
        return "?"
    fields = sorted(st["fields"], key=lambda f: (f["off"] if f["off"] is not None else 1 << 30))
    return " ".join(field_sig(f, structs, depth) for f in fields)


def load(folder):
    out = {}
    for path in glob.glob(os.path.join(folder, "*.tree.json")):
        d = json.load(open(path))
        out[d["id"]] = struct_sig(d["structs"][d["root"]], d["structs"])
    return out


def counts133():
    import rofl_packets
    r = rofl_packets.Rofl(os.path.join(ROOT, "data", "rofl", "KR-6363178603_13.3.rofl"))
    c = collections.Counter()
    for e, (t, ch, pid, obj, body) in rofl_packets.stream(r, (1,)):
        c[pid] += 1
    return c, r.game_len / 1000.0


def counts1620():
    import rofl2
    path = os.path.join(os.path.expanduser("~"), "Documents", "League of Legends", "Replays", "EUN1-4013530370.rofl")
    r = rofl2.Rofl2(path)
    c = collections.Counter()
    last = 0.0
    for e, (t, ch, pid, obj, body) in rofl2.stream(r, (1,)):
        c[pid] += 1
        last = max(last, t)
    return c, last


def main():
    a, b = load(os.path.join(ROOT, "data", "exe133", "codec")), load(os.path.join(ROOT, "data", "exe1620", "codec"))
    ca, la = counts133()
    cb, lb = counts1620()
    rate_a = {i: ca[i] / la for i in a}
    rate_b = {i: cb[i] / lb for i in b}
    by_a, by_b = collections.defaultdict(list), collections.defaultdict(list)
    for i, s in a.items():
        by_a[s].append(i)
    for i, s in b.items():
        by_b[s].append(i)
    rows, used_b, result = [], set(), {}
    for s, ids in sorted(by_a.items(), key=lambda x: min(x[1])):
        cand = by_b.get(s, [])
        if len(ids) == 1 and len(cand) == 1:
            rows.append((ids[0], cand[0], "unique", s))
            used_b.add(cand[0])
            result[ids[0]] = {"id": cand[0], "how": "unique"}
        elif cand:
            # pair by rate rank inside the group
            xa = sorted(ids, key=lambda i: -rate_a[i])
            xb = sorted(cand, key=lambda i: -rate_b[i])
            for k, i in enumerate(xa):
                if k < len(xb):
                    note = f"by count ({len(ids)} x 13.3, {len(cand)} x 16.20 share the shape; rates {rate_a[i]:.2f}/s vs {rate_b[xb[k]]:.2f}/s)"
                    rows.append((i, xb[k], note, s))
                    used_b.add(xb[k])
                    result[i] = {"id": xb[k], "how": "by count", "group": [xa, xb]}
                else:
                    rows.append((i, None, "no 16.20 id left in its shape group", s))
        else:
            for i in ids:
                rows.append((i, None, "", s))
    # near matches for the rest
    free_b = {i: s for i, s in b.items() if i not in used_b}
    for k, (i, j, how, s) in enumerate(rows):
        if j is not None:
            continue
        best = None
        ta = s.split()
        for jb, sb in free_b.items():
            r = difflib.SequenceMatcher(None, ta, sb.split()).ratio()
            if best is None or r > best[0]:
                best = (r, jb, sb)
        if best and best[0] >= 0.75:
            rows[k] = (i, best[1], f"near ({best[0]:.2f})", s + "   ||   " + best[2])
            result[i] = {"id": best[1], "how": f"near {best[0]:.2f}"}
    out = os.path.join(ROOT, "data", "exe1620", "id_map.txt")
    with open(out, "w") as f:
        kinds = collections.Counter(r[2].split(" (")[0] if r[1] is not None else "none" for r in rows)
        f.write(f"13.3 formats {len(a)}, 16.20 formats {len(b)}; matches: {dict(kinds)}\n")
        for i, j, how, s in sorted(rows):
            f.write(f"{i:5} -> {j if j is not None else '-':>5}  {how or 'no match':60}  {s[:150]}\n")
        f.write("\n16.20 ids with a learnt format and no 13.3 partner:\n")
        taken = {r[1] for r in rows}
        for j in sorted(b):
            if j not in taken:
                f.write(f"      {j:5}  {rate_b[j]:8.2f}/s  {b[j][:150]}\n")
    json.dump(result, open(out[:-4] + ".json", "w"), indent=0)
    print(open(out).readline().strip())


if __name__ == "__main__":
    main()
