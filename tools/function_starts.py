"""Function starts missing from client-src/functions.txt, and the list completed.

functions.txt was made from call targets, so it lacks functions that are only ever jumped to (tail calls) or reached
through a pointer kept in data or pushed as an argument (atexit callbacks). Such a start is accepted here when all of this holds: something outside the function
it would otherwise belong to jumps to it with a jmp rel32, a relocated pointer in a data section points at it, or a push imm32 pushes it; it is
16-byte aligned; and the byte before it is int3 padding.

  function_starts.py            how many there are (and how many Ghidra's analysis also has as functions)
  function_starts.py write      add them to client-src/functions.txt
"""
import bisect
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import packet_emu as P  # noqa: E402

TEXT0, TEXT1 = 0x1000, 0x1000 + 0xfa96ec
LIST = os.path.join(ROOT, 'client-src', 'functions.txt')


def data_pointers(img):
    """Targets in .text of the relocated pointers that sit outside .text (unpacked exe's relocation table)."""
    d = open(os.path.join(ROOT, 'game', 'League of Legends.unpacked.exe'), 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3c)[0]
    nsec, opt = struct.unpack_from('<H', d, pe + 6)[0], struct.unpack_from('<H', d, pe + 20)[0]
    out = set()
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        if d[o:o + 8].rstrip(b'\0') != b'.reloc':
            continue
        size, _, raw_size, raw = struct.unpack_from('<IIII', d, o + 8)
        o, end = raw, raw + min(size, raw_size)
        while o < end:
            page, block = struct.unpack_from('<II', d, o)
            if block < 8:
                break
            for k in range((block - 8) // 2):
                e = struct.unpack_from('<H', d, o + 8 + 2 * k)[0]
                if e >> 12 == 3:
                    at = page + (e & 0xfff)
                    v = struct.unpack_from('<I', img, at)[0] - P.BASE
                    if TEXT0 <= v < TEXT1 and not TEXT0 <= at < TEXT1:
                        out.add(v)
            o += block
    return out


def missing():
    img = bytes(P.IMG)
    known = sorted(int(x, 16) for x in open(LIST).read().split())
    have = set(known)
    targets = data_pointers(img)
    i = img.find(b'\xe9', TEXT0)
    while 0 <= i < TEXT1 - 5:
        t = i + 5 + struct.unpack_from('<i', img, i + 1)[0]
        if TEXT0 <= t < TEXT1:
            k = bisect.bisect_right(known, i) - 1
            if not known[k] <= t < (known[k + 1] if k + 1 < len(known) else TEXT1):
                targets.add(t)
        i = img.find(b'\xe9', i + 1)
    # code addresses pushed as an argument (push imm32): the callbacks given to atexit by the dynamic initializers,
    # thread procedures, ...
    i = img.find(b'\x68', TEXT0)
    while 0 <= i < TEXT1 - 5:
        t = struct.unpack_from('<I', img, i + 1)[0] - P.BASE
        if TEXT0 <= t < TEXT1:
            targets.add(t)
        i = img.find(b'\x68', i + 1)
    return known, sorted(t for t in targets - have if t % 16 == 0 and img[t - 1] == 0xcc)


def main():
    known, new = missing()
    ghidra = set()
    index = os.path.join(ROOT, 'client-src', 'decomp', 'index.tsv')
    if os.path.exists(index):
        ghidra = {int(line.split('\t')[0], 16) for line in open(index) if line[0] != '#'}
    print(f'{len(known)} starts in functions.txt, {len(new)} more found'
          + (f' ({sum(1 for t in new if t in ghidra)} of them are functions in the Ghidra export too)' if ghidra else ''))
    if sys.argv[1:] == ['write'] and new:
        with open(LIST, 'w', newline='\n') as f:
            f.write(''.join(f'{t:#x}\n' for t in sorted(known + new)))
        print(f'functions.txt now has {len(known) + len(new)} starts')


if __name__ == '__main__':
    main()
