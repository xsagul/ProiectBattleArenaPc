"""The client built from our sources where we have them and from Riot's bytes everywhere else.

Every function of client-src/src/ that tools/match_all.py finds identical is compiled with Riot's compiler, its
relocations are filled in from client-src/symbols.tsv (our symbol -> client address, written by match_all.py) and the
result is written over the same function in a copy of the unpacked exe. Unlike the comparison in match_func.py, nothing
is skipped here: the bytes written are the complete linked function, and they have to equal the client's. The output
is therefore the same file as the input for as long as the sources are right - the point is that a growing part of it
comes out of a compiler, and that any mistake in a relocated field shows up as a difference.

Fields this script cannot compute (offsets into the client's thread-local storage) are taken from the client and
counted.

  build_hybrid.py            builds client-src/obj/League of Legends.hybrid.exe and reports
"""
import glob
import hashlib
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import packet_emu as P  # noqa: E402

EXE = os.path.join(ROOT, 'game', 'League of Legends.unpacked.exe')
OUT = os.path.join(ROOT, 'client-src', 'obj', 'League of Legends.hybrid.exe')


def file_offset(exe):
    pe = struct.unpack_from('<I', exe, 0x3c)[0]
    nsec, opt = struct.unpack_from('<H', exe, pe + 6)[0], struct.unpack_from('<H', exe, pe + 20)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + 40 * i
        vsize, va, rsize, raw = struct.unpack_from('<IIII', exe, o + 8)
        secs.append((va, max(vsize, rsize), raw))

    def at(rva):
        for va, size, raw in secs:
            if va <= rva < va + size:
                return raw + rva - va
        raise ValueError(hex(rva))
    return at


def main():
    symbols = {}
    for line in open(os.path.join(ROOT, 'client-src', 'symbols.tsv')):
        if line[0] != '#':
            sym, rva, _ = line.rstrip('\n').split('\t')
            symbols.setdefault(sym, int(rva, 16))
    exe = bytearray(open(EXE, 'rb').read())
    at = file_offset(exe)
    objs, built, size, borrowed, wrong = {}, 0, 0, 0, []
    for src in M.sources():
        for m in re.finditer(r'^// match: ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
            flags = m.group(3).split() or M.file_flags(src)
            key = (src, tuple(flags))
            if key not in objs:
                objs[key] = M.compile_obj(src, flags)
            rva = int(m.group(1), 16)
            if M.compare(src, m.group(2), rva, flags, objs[key])[3] is not None:
                continue                                            # not identical yet: Riot's bytes stay
            name, code, _ = M.function_of(objs[key], m.group(2))
            code = bytearray(code)
            while code and code[-1] in (0xcc, 0x90) and len(code) - 1 not in M.TARGETS:
                code.pop()
            for off, (typ, sym) in M.TARGETS.items():
                if off + 4 > len(code):
                    continue
                addend = struct.unpack_from('<i', code, off)[0]
                if typ == 0x14 and sym in symbols:
                    value = symbols[sym] + addend - (rva + off + 4)
                elif typ == 6 and sym in symbols:
                    value = P.BASE + symbols[sym] + addend
                else:
                    value = struct.unpack_from('<i', P.IMG, rva + off)[0]
                    borrowed += 1
                struct.pack_into('<I', code, off, value & 0xffffffff)
            if bytes(code) != bytes(P.IMG[rva:rva + len(code)]):
                bad = next(i for i in range(len(code)) if code[i] != P.IMG[rva + i])
                wrong.append(f'{rva:#x} {name[:50]}: linked bytes differ from the client at +{bad:#x}')
                continue
            o = at(rva)
            exe[o:o + len(code)] = code
            built += 1
            size += len(code)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(exe)
    same = hashlib.sha256(exe).digest() == hashlib.sha256(open(EXE, 'rb').read()).digest()
    for w in wrong:
        print(' ', w)
    print(f'{built} functions, {size} bytes of code written from our sources'
          f' ({borrowed} relocated fields taken from the client, {len(wrong)} functions refused)')
    print(f'{OUT}: {"identical to" if same else "DIFFERENT from"} the unpacked client ({len(exe)} bytes)')
    return 0 if same and not wrong else 1


if __name__ == '__main__':
    sys.exit(main())
