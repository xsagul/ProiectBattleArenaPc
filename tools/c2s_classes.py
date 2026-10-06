"""Every client -> server packet class of the 13.3 client: id, constructor, writer.

A C2S constructor stores the packet id (mov eax, <id>; mov [obj+4], ax) right after the base vtable (rva 0xfb357c),
then its own vtable; the writer is that vtable's slot 0. Found by scanning the unpacked image for the base vtable
store; the constructor is the function holding it (client-src/functions.txt).

  c2s_classes.py [id ...]       -> data/exe133/c2s_classes.txt (id ctor writer)
"""
import bisect
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import packet_emu as P  # noqa: E402

RES = os.path.join(HERE, '..', 'data', 'exe133')
BASE_VT = P.BASE + 0xfb357c


def main():
    funcs = sorted(int(x, 16) for x in open(os.path.join(RES, '..', '..', 'client-src', 'functions.txt')).read().split())
    img = P.IMG
    needle = struct.pack('<I', BASE_VT)
    out = {}
    at = 0
    while True:
        at = img.find(needle, at)
        if at < 0:
            break
        # c7 /0 [reg] imm32: the imm32 starts 2 bytes after the opcode (no displacement) or 3 (disp8)
        ok = img[at - 2] == 0xc7 or img[at - 3] == 0xc7
        if ok:
            back = img[max(0, at - 32):at]
            k = back.rfind(b'\xb8')         # mov eax, imm32 (the id)
            pid = struct.unpack_from('<I', back, k + 1)[0] if k >= 0 and k + 5 <= len(back) else None
            fwd = img[at + 4:at + 40]
            vt = None
            for j in range(len(fwd) - 6):
                if fwd[j] == 0xc7 and fwd[j + 1] in range(0x00, 0x08):
                    cand = struct.unpack_from('<I', fwd, j + 2)[0]
                    if cand != BASE_VT and P.BASE < cand < P.BASE + len(img):
                        vt = cand
                        break
            if pid is not None and pid < 2000 and vt:
                fn = funcs[bisect.bisect_right(funcs, at) - 1]
                writer = struct.unpack_from('<I', img, vt - P.BASE)[0] - P.BASE
                out.setdefault(pid, (fn, writer, vt - P.BASE))
        at += 4
    lines = [f'{pid} {fn:#x} {w:#x} vtable {vt:#x}' for pid, (fn, w, vt) in sorted(out.items())]
    open(os.path.join(RES, 'c2s_classes.txt'), 'w').write('\n'.join(lines) + '\n')
    want = {int(x) for x in sys.argv[1:]}
    print(len(out), 'classes')
    for line in lines:
        if not want or int(line.split()[0]) in want:
            print(line)


if __name__ == '__main__':
    main()
