"""Downloads whole .wad.client archives from Riot's official CDN through the game's release manifest, into the same
layout as a League install (game-data/DATA/FINAL/...), so the client reads them exactly like League reads its own.

    python tools/fetch_wads.py Champions/Garen.wad.client DATA.wad.client Scripts.wad.client

The manifest and the chunk reader are BattleArena's (Desktop/BattleArena/tools/lolcdn.py). Chunks that sit next to each
other in the same bundle are fetched in one range request.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BA = os.path.join(os.path.dirname(ROOT), 'BattleArena')
sys.path.insert(0, os.path.join(BA, 'tools'))
import zstandard  # noqa: E402
from lolcdn import CDN, Manifest, http_get  # noqa: E402

MANIFEST = os.path.join(BA, 'art', 'lol-mapgeo', 'release.manifest')
OUT = os.path.join(ROOT, 'game-data')


def fetch(m, f, dest):
    tmp = dest + '.part'
    dctx = zstandard.ZstdDecompressor()
    chunks = [m.chunks[c] for c in f['chunks']]
    done = 0
    with open(tmp, 'wb') as out:
        i = 0
        while i < len(chunks):
            bid, off, csize, usize = chunks[i]
            # extend the run while the next chunk follows in the same bundle
            j = i + 1
            end = off + csize
            while j < len(chunks) and chunks[j][0] == bid and chunks[j][1] == end and end - off < 8 << 20:
                end += chunks[j][2]
                j += 1
            data = http_get(f"{CDN}/bundles/{bid:016X}.bundle", (off, end - 1))
            p = 0
            for k in range(i, j):
                _, _, cs, us = chunks[k]
                out.write(dctx.decompress(data[p:p + cs], max_output_size=us))
                p += cs
                done += us
            i = j
            print(f"\r  {done / 1e6:7.1f} / {f['size'] / 1e6:.1f} MB", end='', flush=True)
    print()
    if os.path.getsize(tmp) != f['size']:
        raise RuntimeError(f"size mismatch for {dest}")
    os.replace(tmp, dest)


def main():
    m = Manifest(MANIFEST)
    for name in sys.argv[1:]:
        matches = [f for f in m.files if m.path(f).lower().endswith('data/final/' + name.lower())]
        if len(matches) != 1:
            print('not found (or ambiguous):', name)
            continue
        f = matches[0]
        dest = os.path.join(OUT, *m.path(f).split('/'))
        if os.path.exists(dest) and os.path.getsize(dest) == f['size']:
            print('have', m.path(f))
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print('fetching', m.path(f), f"({f['size'] / 1e6:.1f} MB)")
        fetch(m, f, dest)


if __name__ == '__main__':
    main()
