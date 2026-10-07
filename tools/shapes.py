"""Group the client's functions by code shape: the bytes of a function with every address left out (call / jmp
targets, absolute addresses into the image). Functions with the same shape are one piece of source compiled for
several types or callees (template instantiations, std::function / lambda plumbing, copies of an inline helper), so
one reconstructed source covers the whole group.

  shapes.py [min bytes]      -> client-src/shapes.tsv (shape id, members, bytes each, rvas), largest groups first,
                                and a summary of how much code sits in groups of 2+
"""
import bisect
import collections
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402

TEXT1 = 0x1000 + 0xfa96ec
IMAGE_END = 0x3277000


def bounds(img, starts):
    """[(rva, size)] for every function start, trailing int3 padding left out."""
    out = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else TEXT1
        while e > s and img[e - 1] == 0xcc:
            e -= 1
        out.append((s, e - s))
    return out


def shape(img, rva, size, md):
    """The function's bytes with addresses replaced by zero bytes; None if it does not disassemble cleanly."""
    import packet_emu as P
    code = bytearray(img[rva:rva + size])
    end = 0
    for ins in md.disasm(bytes(code), rva):
        end = ins.address + ins.size - rva
        o = ins.address - rva
        b = ins.bytes
        if b[0] in (0xe8, 0xe9) and ins.size == 5:              # call / jmp rel32
            t = int(ins.op_str, 16) if ins.op_str.startswith('0x') else None
            if b[0] == 0xe8 or t is None or not rva <= t < rva + size:
                code[o + 1:o + 5] = b'\0\0\0\0'
            continue
        # any 4-byte field holding an absolute address into the image
        for j in range(max(1, ins.size - 8), ins.size - 3):
            v = int.from_bytes(b[j:j + 4], 'little')
            if P.BASE + 0x1000 <= v < P.BASE + IMAGE_END:
                code[o + j:o + j + 4] = b'\0\0\0\0'
    if end != size:
        return None
    return bytes(code)


def main():
    import packet_emu as P
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    img = bytes(P.IMG)
    starts = sorted(M.starts())
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    groups = collections.defaultdict(list)
    bad = 0
    for rva, size in bounds(img, starts):
        if size < lo:
            continue
        s = shape(img, rva, size, md)
        if s is None:
            bad += 1
            continue
        groups[hashlib.sha1(s).hexdigest()[:12]].append((rva, size))
    rows = sorted(groups.items(), key=lambda kv: -len(kv[1]) * kv[1][0][1])
    out = os.path.join(ROOT, 'client-src', 'shapes.tsv')
    with open(out, 'w', newline=chr(10)) as f:
        f.write(chr(9).join(['# shape', 'members', 'bytes each', 'rvas']) + chr(10))
        for h, mem in rows:
            if len(mem) > 1:
                f.write(chr(9).join([h, str(len(mem)), str(mem[0][1]), ' '.join(f'{r:x}' for r, _ in mem)]) + chr(10))
    multi = [m for m in groups.values() if len(m) > 1]
    print(f'{len(groups)} shapes over {sum(len(m) for m in groups.values())} functions ({bad} did not disassemble)')
    print(f'groups of 2+: {len(multi)} shapes, {sum(len(m) for m in multi)} functions, '
          f'{sum(len(m) * m[0][1] for m in multi)} bytes; covered by one source each: '
          f'{sum((len(m) - 1) * m[0][1] for m in multi)} bytes beyond the first member')
    for lim in (2, 5, 20, 100):
        g = [m for m in multi if len(m) >= lim]
        print(f'  {lim:>3}+ members: {len(g)} shapes, {sum(len(m) for m in g)} functions, '
              f'{sum(len(m) * m[0][1] for m in g)} bytes')
    print('->', out)


if __name__ == '__main__':
    main()
