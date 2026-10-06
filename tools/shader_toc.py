"""League's shader permutation tables (TOC3.0, the `<shader>.ps.dx11` / `.vs.dx11` entries of ShaderCache wads).

Layout (read off patch 14.1's files): u32 6 + "TOC3.0", u32 table size, u32 define count, u32 compiled shader count,
u32 1, string "baseDefines", define count x (string name, string value), string "shaders", then table size x u64 key
and table size x u32 shader index. Strings are u32 length + bytes. The compiled shaders are the DXBC blobs of the
`<shader>.ps.dx11_<n>` entries, 100 per entry, in index order.

A key is the xxHash64 of the permutation's defines written NAME=VALUE, sorted, joined with nothing in between
(found by search: research/toc_hash_search.py). Decoding tries every combination of the TOC's own defines, so each
table entry gets its exact define set.

  python tools/shader_toc.py <toc file> [--json out.json]
"""
import itertools
import json
import struct
import sys

import xxhash


def read_toc(data):
    at = 4 + 6
    size, n_defines, n_shaders, _groups = struct.unpack_from('<4I', data, at)
    at += 16

    def s32():
        nonlocal at
        n = struct.unpack_from('<I', data, at)[0]
        at += 4
        v = data[at:at + n].decode('latin-1')
        at += n
        return v

    s32()  # "baseDefines"
    defines = [(s32(), s32()) for _ in range(n_defines)]
    s32()  # "shaders"
    keys = struct.unpack_from('<%dQ' % size, data, at)
    index = struct.unpack_from('<%dI' % size, data, at + 8 * size)
    return defines, n_shaders, dict(zip(keys, index))


def key_of(defines):
    return xxhash.xxh64(''.join(f'{n}={v}' for n, v in sorted(defines)).encode()).intdigest()


def decode(defines, table):
    """{shader index: [define sets]} for every table key a combination of the TOC's defines reproduces."""
    by_name = {}
    for n, v in defines:
        by_name.setdefault(n, []).append(v)
    names = sorted(by_name)
    out = {}
    found = 0
    for choice in itertools.product(*[[None] + by_name[n] for n in names]):
        combo = [(n, v) for n, v in zip(names, choice) if v is not None]
        k = key_of(combo)
        if k in table:
            out.setdefault(table[k], []).append(combo)
            found += 1
    return out, found


def main():
    data = open(sys.argv[1], 'rb').read()
    defines, n_shaders, table = read_toc(data)
    out, found = decode(defines, table)
    print(f'{len(table)} keys, {found} decoded, {len(out)} of {n_shaders} shaders reached')
    if '--json' in sys.argv:
        path = sys.argv[sys.argv.index('--json') + 1]
        json.dump({str(i): [dict(c) for c in combos] for i, combos in sorted(out.items())}, open(path, 'w'), indent=0)


if __name__ == '__main__':
    main()
