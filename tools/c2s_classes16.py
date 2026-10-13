"""Every packet class the 16.20 client writes itself (client -> server): id, writer, vtable, where it is built.

A client packet's writer (vtable slot 0) starts by writing the packet id through rva 0x11e3870 (the mirror of the
id reader 0x11c4ae0: one byte below 251, else two). So: every function that calls 0x11e3870 is a writer; the
vtable is where its address stands in .rdata; the id is the constant stored at +8 of the object where that
vtable is set (as a 16-bit or a 32-bit store).

    python tools/c2s_classes16.py      -> data/exe1620/c2s_classes.txt   (id, writer, vtable, building site)
"""
import collections, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import packet_emu16 as P   # noqa: E402
import capstone            # noqa: E402

ID_WRITER = 0x11e3870


def rel32_refs(img, lo, hi, targets):
    """rva of every 4-byte displacement in [lo, hi) that lands on a target -> {target: [site]}"""
    out = collections.defaultdict(list)
    for m in re.finditer(rb"(?=(....))", img[lo:hi], re.S):
        o = lo + m.start()
        t = o + 4 + struct.unpack("<i", m.group(1))[0]
        if t in targets:
            out[t].append(o)
    return out


def main():
    img = P.IMG
    text_size, text_at = P._SECS[".text"]
    rdata_size, rdata_at = P._SECS[".rdata"]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    # 1. writers: functions with a direct call to the id writer
    writers = set()
    for site in rel32_refs(img, text_at, text_at + text_size, {ID_WRITER})[ID_WRITER]:
        if img[site - 1] == 0xe8:
            writers.add(P.fn_of(site))
    # 2. vtables: where a writer's address stands in .rdata (slot 0 = the address before it is not code of its own class)
    vt_of = {}
    for o in range(rdata_at, rdata_at + rdata_size - 8, 8):
        v = struct.unpack_from("<Q", img, o)[0] - P.BASE
        if v in writers:
            vt_of.setdefault(v, []).append(o)
    # 3. where each vtable is put into an object, and the id stored at +8 next to it
    all_vts = {o for v in vt_of.values() for o in v}
    refs = rel32_refs(img, text_at, text_at + text_size, all_vts)
    rows, no_id = [], 0
    for w in sorted(vt_of):
        ids = collections.Counter()
        where = {}
        for vt in vt_of[w]:
            for site in refs.get(vt, []):
                lo = max(text_at, site - 90)
                for back in range(0, 16):          # find an instruction boundary that decodes up to the lea
                    ins = list(md.disasm(img[lo + back:site + 120], P.BASE + lo + back))
                    if any(i.address - P.BASE <= site < i.address - P.BASE + i.size and i.mnemonic == "lea" for i in ins):
                        break
                else:
                    continue
                regs = {}       # 32-bit register -> the constant last put in it
                low = {"ax": "eax", "cx": "ecx", "dx": "edx", "bx": "ebx", "si": "esi", "di": "edi", "r8w": "r8d", "r9w": "r9d",
                       "r10w": "r10d", "r11w": "r11d", "r12w": "r12d", "r13w": "r13d", "r14w": "r14d", "r15w": "r15d", "bp": "ebp"}
                for i in ins:
                    if i.mnemonic != "mov":
                        continue
                    m = re.match(r"(word|dword) ptr \[(\w+) \+ (8|0x[0-9a-f]+)\], (0x[0-9a-f]+|\d+)$", i.op_str)
                    if m and (m.group(3) == "8" or m.group(3).endswith("8")):
                        val = int(m.group(4), 0) & 0xffff
                        if 0 < val < 1401:
                            ids[val] += 2
                            where.setdefault(val, site)
                        continue
                    m = re.match(r"(e[a-ds][xip]|r\d+d), (0x[0-9a-f]+|\d+)$", i.op_str)
                    if m:
                        regs[m.group(1)] = int(m.group(2), 0)
                        continue
                    # the id put in a register first, then stored as a word (objects built on the stack)
                    m = re.match(r"word ptr \[[^\]]+\], (\w+)$", i.op_str)
                    if m and low.get(m.group(1)) in regs:
                        val = regs[low[m.group(1)]]
                        if 0 < val < 1401 and abs((i.address - P.BASE) - site) < 48:
                            ids[val] += 1
                            where.setdefault(val, site)
        if not ids:
            no_id += 1
            rows.append((None, w, vt_of[w][0], None))
            continue
        pid = ids.most_common(1)[0][0]
        rows.append((pid, w, vt_of[w][0], where[pid]))
    s2c = set(P.table())
    out = os.path.join(ROOT, "data", "exe1620", "c2s_classes.txt")
    with open(out, "w") as f:
        for pid, w, vt, site in sorted(rows, key=lambda r: (r[0] is None, r[0] or 0, r[1])):
            f.write(f"{pid if pid is not None else '?':>5} writer {w:08x} vtable {vt:08x} built at {f'{site:08x}' if site else '-':>8}"
                    f"{'  (id also has a server class)' if pid in s2c else ''}\n")
    got = {r[0] for r in rows if r[0] is not None}
    print(f"{len(writers)} writers, {len(vt_of)} with a vtable, {len(got)} ids found, {no_id} writers without an id")
    seen = (1, 64, 66, 197, 251, 431, 807, 841, 1027, 1032, 1034, 1042, 1046, 1084, 1148, 1185)
    print("ids the client was seen sending:", {p: (p in got) for p in seen})


if __name__ == "__main__":
    main()
