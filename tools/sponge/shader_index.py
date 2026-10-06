"""Names every compiled shader of a ShaderCache.dx11 wad by the xxh64 of its DXBC (the hash the GPU sponge records),
with its permutation's defines from the shader's TOC.

  python tools/sponge/shader_index.py <ShaderCache.dx11.wad.client> <out.json> [captured shaders dir ...]

With captured shader dirs (research/sponge/<tag>/shaders), only cache blobs of a captured shader's size are hashed and
only the matching shaders' TOCs decoded (fast); the out file is merged with what it already holds.

Out: {"<fnv64 hex>": {"shader": "assets/shaders/generated/shaders/particles/quad", "stage": "ps", "index": 17,
                       "defines": [["ALPHA_TEST", "1"], ...]}}
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wadx import Wad  # noqa: E402
import shader_toc  # noqa: E402
import xxhash  # noqa: E402

HASHES = r'C:/Users/Sorin/Desktop/BattleArena/art/lol-data/hashes.game.txt'


def fnv64(b):
    h = 0xcbf29ce484222325
    for x in b:
        h = ((h ^ x) * 0x100000001b3) & 0xffffffffffffffff
    return h


def split_dxbc(data):
    out, at = [], 0
    while at + 28 <= len(data):
        if data[at:at + 4] != b'DXBC':
            at += 1
            continue
        size = struct.unpack_from('<I', data, at + 24)[0]
        if size <= 32 or at + size > len(data):
            at += 4
            continue
        out.append(data[at:at + size])
        at += size
    return out


def main():
    wad = Wad(sys.argv[1])
    out_path = sys.argv[2]
    wanted = {}
    for d in sys.argv[3:]:
        for f in os.listdir(d):
            if f.endswith('.dxbc'):
                wanted.setdefault(os.path.getsize(os.path.join(d, f)), set()).add(f[:-5])
    index = json.load(open(out_path)) if os.path.exists(out_path) else {}
    names = {}
    for line in open(HASHES, encoding='utf8', errors='replace'):
        h, _, n = line.rstrip(chr(10)).partition(' ')
        if 'shaders/' in n and '.dx11' in n:
            try:
                names[int(h, 16)] = n
            except ValueError:
                pass
    tocs = {n: h for h, n in names.items() if re.search(r'\.(vs|ps)\.dx11$', n) and h in wad.entries}
    matched = 0
    for toc_name, th in sorted(tocs.items()):
        base = toc_name[:-len('.ps.dx11')]
        stage = toc_name[-7:-5]
        hits = []
        for i in range(0, 20000, 100):
            h = xxhash.xxh64(f'{toc_name}_{i}'.encode()).intdigest()
            if h not in wad.entries:
                if i > 0:
                    break
                continue
            for k, blob in enumerate(split_dxbc(wad.read(h))):
                if wanted and len(blob) not in wanted:
                    continue
                fh = '%016x' % xxhash.xxh64(blob).intdigest()
                if wanted and fh not in wanted[len(blob)]:
                    continue
                hits.append((fh, i + k))
        if not hits:
            continue
        try:
            defines, _, table = shader_toc.read_toc(wad.read(th))
            by_index = shader_toc.decode(defines, table)[0] if len(defines) <= 18 else {}
        except Exception as e:  # noqa: BLE001
            print('toc', toc_name, e)
            by_index = {}
        for fh, idx in hits:
            index[fh] = {'shader': base, 'stage': stage, 'index': idx, 'defines': (by_index.get(idx) or [[]])[0]}
            matched += 1
    json.dump(index, open(out_path, 'w'), indent=0)
    print(len(tocs), 'shaders in the cache,', matched, 'matched now,', len(index), 'in the index')


if __name__ == '__main__':
    main()
