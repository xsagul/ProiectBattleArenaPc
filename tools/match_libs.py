"""Which functions of the 13.3 client are library code: every function of the static libraries Riot linked (the VC
runtime of MSVC 14.32 and the ucrt of Windows SDK 10.0.19041, the builds named by the client's Rich header) is
compared, byte by byte, with the client's functions. Bytes under a relocation are left out; the rest must be equal
over the whole function, which must start at a function start of client-src/functions.txt and end where the client's
function ends (padding or the next function start).

Result: client-src/lib_functions.tsv (rva, bytes, library, object, symbol, how many library functions have these same
bytes, their symbols). Functions shorter than MIN bytes are not reported: too short to tell apart.

  match_libs.py
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402

MIN = 8            # bytes outside relocations a function needs to be reported
VC = os.path.join(M.MSVC, 'lib', 'x86')
UCRT = os.path.join(ROOT, 'toolchain', 'winsdk-10.0.19041', 'Windows Kits', '10', 'Lib', '10.0.19041.0', 'ucrt', 'x86')
LIBS = [os.path.join(VC, 'libcmt.lib'), os.path.join(VC, 'libvcruntime.lib'), os.path.join(VC, 'libcpmt.lib'),
        os.path.join(UCRT, 'libucrt.lib')]


def members(path):
    d = open(path, 'rb').read()
    longnames, i = b'', 8
    while i < len(d):
        name, size = d[i:i + 16], int(d[i + 48:i + 58])
        body = d[i + 60:i + 60 + size]
        if name[:2] == b'//':
            longnames = body
        elif name[:1] == b'/' and name[1:2].isdigit():
            o = int(name[1:].split()[0])
            yield longnames[o:longnames.index(b'\0', o)].decode(), body
        elif name[:1] != b'/':
            yield name.split(b'/')[0].decode(), body
        i += 60 + size + (size & 1)


def functions(obj):
    """(symbol, code bytes, relocated offsets) of every function in one COFF object."""
    if len(obj) < 20:
        return
    machine, nsec, _, symptr, nsym, opt = struct.unpack_from('<HHIIIH', obj, 0)
    if machine != 0x14c or not symptr:
        return
    strtab = symptr + 18 * nsym
    syms, k = [], 0
    while k < nsym:
        s = obj[symptr + 18 * k:symptr + 18 * k + 18]
        value, sec, typ, cls, aux = struct.unpack_from('<IhHBB', s, 8)
        if s[:4] == b'\0\0\0\0':
            o = strtab + struct.unpack_from('<I', s, 4)[0]
            name = obj[o:obj.index(b'\0', o)].decode('latin1')
        else:
            name = s[:8].rstrip(b'\0').decode('latin1')
        if sec > 0 and cls in (2, 3) and not name.startswith(('.', '$')):
            syms.append((sec, value, name, typ))
        k += 1 + aux
    by_sec = collections.defaultdict(list)
    for sec, value, name, typ in syms:
        by_sec[sec].append((value, name, typ))
    for sec, lst in by_sec.items():
        h = 20 + opt + 40 * (sec - 1)
        size, raw, relptr = struct.unpack_from('<III', obj, h + 16)
        nrel, flags = struct.unpack_from('<H', obj, h + 32)[0], struct.unpack_from('<I', obj, h + 36)[0]
        if not flags & 0x20 or not raw:                         # code sections only
            continue
        rels = sorted(struct.unpack_from('<I', obj, relptr + 10 * i)[0] for i in range(nrel))
        lst.sort()
        starts = sorted({v for v, _, t in lst if t == 0x20})    # labels inside a function do not end it
        for value, name, typ in lst:
            if typ != 0x20:
                continue
            end = min([v for v in starts if v > value] + [size])
            code = obj[raw + value:raw + end]
            while code and code[-1] == 0xcc:
                code = code[:-1]
            rel = set()
            for off in rels:
                if value <= off < value + len(code):
                    rel.update(range(off - value, min(off - value + 4, len(code))))
            yield name, code, rel


def main():
    import packet_emu as P
    img = bytes(P.IMG)
    starts = sorted(M.starts())
    startset = set(starts)
    indexes = {}                                    # offset k -> {four bytes at start + k -> function starts}

    def index(k):
        if k not in indexes:
            indexes[k] = collections.defaultdict(list)
            for s in starts:
                indexes[k][img[s + k:s + k + 4]].append(s)
        return indexes[k]
    found = {}                                      # rva -> [(size, lib, object, symbol)]
    total = 0
    for lib in LIBS:
        n = hit = 0
        for member, body in members(lib):
            for name, code, rel in functions(body):
                keep = [i for i in range(len(code)) if i not in rel]
                # the first four bytes in a row that no relocation touches select the candidates
                k = next((i for i in range(len(code) - 3) if not rel & {i, i + 1, i + 2, i + 3}), None)
                if len(keep) < MIN or k is None or k > 64:
                    continue
                n += 1
                for s in index(k).get(code[k:k + 4], ()):
                    e = s + len(code)
                    if all(img[s + i] == code[i] for i in keep) and (e in startset or img[e] == 0xcc):
                        found.setdefault(s, []).append((len(code), os.path.basename(lib), os.path.basename(member), name))
                        hit += 1
        total += n
        print(f'{os.path.basename(lib)}: {n} functions with {MIN}+ fixed bytes, {hit} placements in the client')
    out = os.path.join(ROOT, 'client-src', 'lib_functions.tsv')
    rows = []
    for s in sorted(found):
        best = max(found[s])                        # the longest match at this start
        names = sorted({x[3] for x in found[s] if x[0] == best[0]})
        rows.append((s, best, names))
    # the same library function found at several client addresses: template code that differs only in what its
    # relocations point at (another type's vtable, another facet id) - the name is then only "one like this"
    places = collections.Counter(tuple(names) for _, _, names in rows)
    with open(out, 'w', newline=chr(10)) as f:
        f.write(chr(9).join(['# rva', 'bytes', 'library', 'object', 'symbol', 'library functions with these bytes',
                             'their symbols', 'client addresses with this match']) + chr(10))
        for s, best, names in rows:
            f.write(chr(9).join([f'{s:x}', str(best[0]), best[1], best[2], best[3], str(len(names)),
                                 ' '.join(names[:12]), str(places[tuple(names)])]) + chr(10))
    sure = sum(1 for _, _, names in rows if places[tuple(names)] == 1)
    print(f'{sure} of them match a library function found nowhere else in the client')
    size = sum(max(v)[0] for v in found.values())
    print(f'{len(found)} of {len(starts)} client functions are library code, {size} bytes -> {out}')


if __name__ == '__main__':
    main()
