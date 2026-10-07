"""Who calls a function of the unpacked 13.3 client: every "call rel32" / "jmp rel32" in the code that lands on the
given rva, with the function it is in (client-src/functions.txt), that function's size and its name if it has one.

  callers.py <rva hex> [...]
"""
import bisect
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import packet_emu as P  # noqa: E402

TEXT_END = 0xfaa6ec
STARTS = sorted(int(x, 16) for x in open(os.path.join(HERE, '..', 'client-src', 'functions.txt')).read().split())
NAMES = {}
for line in open(os.path.join(HERE, '..', 'client-src', 'names.tsv')):
    p = line.rstrip('\n').split('\t')
    if len(p) == 3 and p[1] == 'func' and p[2]:
        NAMES[int(p[0], 16)] = p[2]


def callers(target):
    img = bytes(P.IMG[:TEXT_END])
    out = {}
    for op in (0xe8, 0xe9):
        i = img.find(bytes([op]), 0x1000)
        while i >= 0:
            if i + 5 + struct.unpack_from('<i', img, i + 1)[0] == target:
                k = bisect.bisect_right(STARTS, i) - 1
                out.setdefault(STARTS[k], []).append(i)
            i = img.find(bytes([op]), i + 1)
    return out


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        t = int(arg, 16)
        found = callers(t)
        print(f'{t:#x} {NAMES.get(t, "")}: {sum(len(v) for v in found.values())} calls from {len(found)} functions')
        for f in sorted(found):
            size = STARTS[bisect.bisect_right(STARTS, f)] - f
            print(f'  {f:#9x} {size:6d} B  {len(found[f])} x  {NAMES.get(f, "")[:60]}')
