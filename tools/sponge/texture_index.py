"""Names the textures the GPU sponge saw: xxh64 of a texture's mip bytes (what d3d11_proxy.c records at CreateTexture2D)
-> the file inside the game's WADs.

  python tools/sponge/texture_index.py <out.json> <wad> [wad ...]

Each .tex / .dds of the given WADs is hashed at mips 0..2 (lower texture quality settings upload from a smaller mip).
The out file is merged with what it already holds: {"<xxh64 hex>": {"path": "assets/...", "wad": "Map11.wad.client",
"mip": 0, "w": 1024, "h": 1024}}
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from wadx import Wad  # noqa: E402
import xxhash  # noqa: E402

HASHES = r'C:/Users/Sorin/Desktop/BattleArena/art/lol-data/hashes.game.txt'


def mip_size(fmt, w, h):
    if fmt == 'bgra':
        return w * h * 4
    return ((w + 3) // 4) * ((h + 3) // 4) * (8 if fmt == 'bc1' else 16)


def mips_of(data):
    """[(mip index, w, h, bytes)] for the first three mips of a TEX or DDS file."""
    out = []
    if data[:3] == b'TEX':
        w, h = struct.unpack_from('<HH', data, 4)
        f = data[9]
        fmt = {10: 'bc1', 11: 'bc1', 12: 'bc3', 20: 'bgra'}.get(f)
        if not fmt:
            return out
        has_mips = data[11] != 0
        if not has_mips:
            return [(0, w, h, data[12:12 + mip_size(fmt, w, h)])]
        n = 1
        m = max(w, h)
        while m > 1:
            m >>= 1
            n += 1
        at = len(data)
        for i in range(n):  # stored smallest first: walk back from the end
            mw, mh = max(w >> i, 1), max(h >> i, 1)
            size = mip_size(fmt, mw, mh)
            at -= size
            if at < 12:
                break
            if i < 3:
                out.append((i, mw, mh, data[at:at + size]))
        return out
    if data[:4] == b'DDS ':
        h, w = struct.unpack_from('<II', data, 12)
        mips = max(struct.unpack_from('<I', data, 28)[0], 1)
        pf_flags, fourcc = struct.unpack_from('<I4s', data, 80)
        if pf_flags & 4:
            fmt = {b'DXT1': 'bc1', b'DXT3': 'bc3', b'DXT5': 'bc3'}.get(fourcc)
            if not fmt:
                return out
        else:
            fmt = 'bgra'
        at = 128
        for i in range(min(mips, 3)):
            mw, mh = max(w >> i, 1), max(h >> i, 1)
            size = mip_size(fmt, mw, mh)
            out.append((i, mw, mh, data[at:at + size]))
            at += size
    return out


def main():
    out_path = sys.argv[1]
    names = {}
    with open(HASHES, encoding='utf-8') as f:
        for line in f:
            h, _, p = line.rstrip('\n').partition(' ')
            if p.endswith(('.tex', '.dds')):
                names[int(h, 16)] = p
    index = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for wad_path in sys.argv[2:]:
        wad = Wad(wad_path)
        base = os.path.basename(wad_path)
        n = 0
        for h in wad.entries:
            p = names.get(h)
            if p is None:
                continue
            try:
                data = wad.read(h)
            except Exception:
                continue
            if not data:
                continue
            for mip, w, hh, b in mips_of(data):
                index['%016x' % xxhash.xxh64(b).intdigest()] = {'path': p, 'wad': base, 'mip': mip, 'w': w, 'h': hh}
            n += 1
        print(base, n, 'textures', flush=True)
    json.dump(index, open(out_path, 'w'))
    print(len(index), 'hashes in', out_path)


if __name__ == '__main__':
    main()
