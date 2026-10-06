"""Looks for how a TOC3.0 shader table keys its permutations: hashes candidate define strings (subsets of the TOC's own
define list, in several spellings) with a few common 64-bit hashes and counts how many land in the table.

  python research/toc_hash_search.py <x.ps.dx11 toc file>
"""
import itertools
import struct
import sys

import xxhash

d = open(sys.argv[1], 'rb').read()
at = 4 + 6
n_entries = struct.unpack_from('<I', d, at)[0]; at += 4
n_defines = struct.unpack_from('<I', d, at)[0]; at += 4
n_shaders = struct.unpack_from('<I', d, at)[0]; at += 4
groups = struct.unpack_from('<I', d, at)[0]; at += 4


def s32():
    global at
    n = struct.unpack_from('<I', d, at)[0]; at += 4
    v = d[at:at + n].decode('latin-1'); at += n
    return v


group = s32()
defines = [(s32(), s32()) for _ in range(n_defines)]
key = s32()
table = set(struct.unpack_from('<%dQ' % n_entries, d, at))
print('entries', n_entries, 'defines', defines, 'shaders', n_shaders)


def fnv64(b):
    h = 0xcbf29ce484222325
    for c in b:
        h = ((h ^ c) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


hashes = {'xxh64': lambda b: xxhash.xxh64(b).intdigest(), 'xxh3': lambda b: xxhash.xxh3_64(b).intdigest(), 'fnv64': fnv64}
items = {'n=v': '{}={}', 'n v': '{} {}', 'def': '#define {} {}\n', 'n': '{}'}
seps = {';': ';', ' ': ' ', 'nl': '\n', ',': ',', '': ''}
names = []
for n, v in defines:
    if (n, v) not in names:
        names.append((n, v))
hits = {}
# subsets of up to 4 defines, in table order and sorted
for k in range(0, 5):
    for combo in itertools.combinations(names, k):
        if len({n for n, _ in combo}) < k:
            continue
        for order in (list(combo), sorted(combo)):
            for iname, ifmt in items.items():
                parts = [ifmt.format(n, v) if '{}' in ifmt[ifmt.index('{}') + 2:] else ifmt.format(n) for n, v in order]
                for sname, sep in seps.items():
                    s = sep.join(parts)
                    for variant in (s, s + sep if sep else s):
                        for case in (variant, variant.lower()):
                            b = case.encode()
                            for hname, h in hashes.items():
                                if h(b) in table:
                                    hits.setdefault((hname, iname, sname), []).append(case)
for k, v in hits.items():
    print('HIT', k, len(v), v[:3])
print('searched; hits:', len(hits))
