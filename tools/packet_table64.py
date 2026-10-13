"""List the 16.20 packet factory: packet id -> case code, object size, class vtable.

    python tools/packet_table64.py <image.bin> <out.txt>

The factory (rva 0xe678c0, found as the function with a 1258-way switch on its second argument)
allocates one object per id, stores the id as a 16-bit word at +8 and sets the class vtable.
"""
import collections, struct, sys
import capstone

img = open(sys.argv[1], "rb").read()
BASE = int(open(sys.argv[1][:-4] + "_pages.txt").readline().split()[1], 16)
FACTORY, TABLE, COUNT, ALLOC = 0xe678c0, 0xe78160, 0x4e9 + 1, 0x1125b70
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def case(rva):
    """(alloc size, id word stored at +8, last vtable stored at [rax], constructor called)"""
    size = idw = vt = ctor = lea = None
    pending = None
    for k, (a, sz, mn, op) in enumerate(md.disasm_lite(img[rva:rva + 400], BASE + rva)):
        if k > 60 or mn in ("jmp", "ret"):
            break
        if mn == "mov" and op.startswith("ecx, 0x") and size is None:
            pending = int(op.split(", ")[1], 16)
        elif mn == "call":
            t = int(op, 16) - BASE if op.startswith("0x") else None
            if t == ALLOC:
                size = pending
            elif t is not None and size is not None and ctor is None:
                ctor = t
        elif mn == "lea" and "rip" in op:
            lea = a + sz + int(op.split("rip")[1].split("]")[0].replace(" ", ""), 16) - BASE
        elif mn == "mov" and op.startswith("qword ptr [rax], r") and lea is not None:
            vt = lea
        elif mn == "mov" and op.startswith("word ptr [rax + 8], "):
            idw = int(op.split(", ")[1], 0)
    return size, idw, vt, ctor


def main():
    targets = [struct.unpack_from("<I", img, TABLE + i * 4)[0] for i in range(COUNT)]
    common = collections.Counter(targets).most_common(1)[0]
    rows, real = [], 0
    for i, t in enumerate(targets):
        if t == common[0]:
            continue
        size, idw, vt, ctor = case(t)
        real += 1
        rows.append(f"{i:5} case {t:08x} size {size if size is not None else '?':>6} idword {idw if idw is not None else '?':>5} "
                    f"vtable {f'{vt:08x}' if vt else '?':>8} ctor {f'{ctor:08x}' if ctor else '-'}")
    open(sys.argv[2], "w").write("\n".join(rows) + "\n")
    print(f"ids 0..{COUNT - 1}: {real} with a class, {common[1]} share the default case {common[0]:#x}")


if __name__ == "__main__":
    main()
