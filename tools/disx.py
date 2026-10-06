"""Disassemble one function of the unpacked 13.3 client by rva, with absolute addresses also shown as rva.

  disx.py <rva hex> [length hex]       the function from client-src/functions.txt (or that many bytes)
"""
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import packet_emu as P  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

md = Cs(CS_ARCH_X86, CS_MODE_32)
FUNCS = sorted(int(x, 16) for x in open(os.path.join(HERE, '..', 'client-src', 'functions.txt')).read().split())


def lines(st, length=None):
    en = st + length if length else FUNCS[bisect.bisect_right(FUNCS, st)]
    out = []
    for i in md.disasm(P.IMG[st:en], P.BASE + st):
        s = f'{i.address - P.BASE:#x} {i.mnemonic} {i.op_str}'

        def fix(m):
            v = int(m.group(0), 16)
            return f'{m.group(0)}(rva {v - P.BASE:#x})' if P.BASE <= v < P.BASE + len(P.IMG) else m.group(0)
        out.append(re.sub(r'0x[0-9a-f]{6,8}', fix, s))
    return out


if __name__ == '__main__':
    print('\n'.join(lines(int(sys.argv[1], 16), int(sys.argv[2], 16) if len(sys.argv) > 2 else None)))
