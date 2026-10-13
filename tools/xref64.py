"""Find code in the 16.20 memory image that refers to a string or an rva.

    python tools/xref64.py <image.bin> str <text> [...]     functions whose code takes the address of a string
    python tools/xref64.py <image.bin> rva <hex> [...]      functions that call / jump to / take the address of an rva
    python tools/xref64.py <image.bin> dis <hex rva> [n]    disassemble n instructions (default 60)

Only rip-relative references and direct call/jmp are followed. Function ranges come from .pdata.
"""
import bisect, struct, sys
import capstone

img = open(sys.argv[1], "rb").read()
BASE = int(open(sys.argv[1][:-4] + "_pages.txt").readline().split()[1], 16) if True else 0
PE = struct.unpack_from("<I", img, 0x3c)[0]
NSEC, OPT = struct.unpack_from("<H", img, PE + 6)[0], struct.unpack_from("<H", img, PE + 20)[0]
SECS = {}
for i in range(NSEC):
    name, vs, va = struct.unpack_from("<8sII", img, PE + 24 + OPT + i * 40)
    SECS[name.rstrip(b"\0").decode()] = (va, vs)
TEXT = SECS[".text"]
FUNCS = []
pd, ps = SECS[".pdata"]
for o in range(pd, pd + ps, 12):
    b, e, _ = struct.unpack_from("<III", img, o)
    if not b:
        break
    FUNCS.append((b, e))
STARTS = [f[0] for f in FUNCS]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)


def func_of(rva):
    i = bisect.bisect_right(STARTS, rva) - 1
    return FUNCS[i] if i >= 0 and FUNCS[i][0] <= rva < FUNCS[i][1] else None


def refs(targets):
    """rva of every 4-byte displacement in .text that lands on one of the targets (rip-relative or rel32)."""
    found = []
    lo, hi = TEXT[0], TEXT[0] + TEXT[1] - 4
    tset = set(targets)
    for o in range(lo, hi):
        d = struct.unpack_from("<i", img, o)[0]
        if o + 4 + d in tset:
            found.append((o, o + 4 + d))
    return found


def dis(rva, n=60):
    for k, (a, sz, mn, op) in enumerate(md.disasm_lite(img[rva:rva + n * 15], BASE + rva)):
        if k >= n:
            break
        note = ""
        if "rip" in op:
            try:
                t = a + sz + int(op.split("rip")[1].split("]")[0].replace(" ", ""), 16) - BASE
                s = img[t:t + 48].split(b"\0")[0]
                note = f"   ; rva {t:#x}" + (f' "{s.decode()}"' if len(s) > 3 and all(32 <= c < 127 for c in s) else "")
            except ValueError:
                pass
        elif op.startswith("0x") and BASE <= int(op, 16) < BASE + len(img):
            op = f"rva {int(op, 16) - BASE:#x}"
        print(f"  {a - BASE:08x} {mn} {op}{note}")


def main():
    mode, args = sys.argv[2], sys.argv[3:]
    if mode == "dis":
        return dis(int(args[0], 16), int(args[1]) if len(args) > 1 else 60)
    targets = {}
    if mode == "str":
        for text in args:
            pos = img.find(text.encode())
            while pos >= 0:
                targets[pos] = text
                pos = img.find(text.encode(), pos + 1)
    else:
        targets = {int(a, 16): a for a in args}
    for at, t in refs(targets):
        f = func_of(at)
        print(f"{targets[t]!r:32} target {t:#x} used at {at:#x} in function {f[0]:#x}..{f[1]:#x}" if f else
              f"{targets[t]!r:32} target {t:#x} used at {at:#x} (no function)")


if __name__ == "__main__":
    main()
