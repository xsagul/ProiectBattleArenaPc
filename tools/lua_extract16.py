"""Riot's Lua scripts of the 16.20 client (game16/DATA/FINAL/Scripts.wad.client) by name -> data/lua1620/

    python tools/lua_extract16.py            scripts/<path with / as __>.luabin64, listing/<same>.txt (luac -l -l),
                                             names.txt (hash -> path), unnamed scripts kept as scripts/_<hash>.luabin64

The manifest (entry 9292a9c26c1abd6b, magic 0MLR, u32 group count [m: 2050]): per character group [u32 len][name]
[u32 count][count x (u32 len, script name)], then a flat list [u32 n][n x (u32 len, path)]. Entry hash = XXH64 of the
lowercase path (data/characters/<group>/spells/<name>.luabin64, data/characters/<group>/<name>.luabin64,
data/characters/<group>/scripts/<name>.luabin64; the flat list's own paths with .lua -> .luabin64).
A script that no manifest name reaches keeps its hash; its listing still shows what it defines.
"""
import os
import struct
import subprocess
import sys

import xxhash

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import wadx

WAD = os.path.join(ROOT, 'game16', 'DATA', 'FINAL', 'Scripts.wad.client')
OUT = os.path.join(ROOT, 'data', 'lua1620')
LUAC = os.path.join(ROOT, 'server', 'lua51', 'luac51.exe')
MANIFEST = 0x9292a9c26c1abd6b


def names(m):
    p = 8
    groups = struct.unpack_from('<I', m, 4)[0]

    def s():
        nonlocal p
        n = struct.unpack_from('<I', m, p)[0]
        p += 4
        v = m[p:p + n].decode(errors='replace')
        p += n
        return v
    out = []
    for _ in range(groups):
        g = s()
        cnt = struct.unpack_from('<I', m, p)[0]
        p += 4
        for _ in range(cnt):
            n = s()
            for fmt in ('data/characters/{g}/spells/{n}', 'data/characters/{g}/{n}', 'data/characters/{g}/scripts/{n}'):
                out.append(fmt.format(g=g, n=n))
    flat = struct.unpack_from('<I', m, p)[0]
    p += 4
    for _ in range(flat):
        out.append(s())
    paths = []
    for x in out:
        x = x.lower()
        if x.endswith('.lua'):
            x = x[:-4]
        if x.endswith('.luabin64'):
            x = x[:-9]
        if '/' not in x:
            # a bare name of the flat list: the folders the memory notes list
            for d in ('data/spells/', 'data/shared/spells/', 'data/items/', 'data/items/spells/', 'data/scripts/',
                      'data/shared/scripts/', 'data/buildingblocks/', 'data/shared/'):
                paths.append(d + x)
        else:
            paths.append(x)
    return paths


def main():
    w = wadx.Wad(WAD)
    known = {}
    for path in names(w.read(MANIFEST)):
        known[xxhash.xxh64((path + '.luabin64').encode()).intdigest()] = path
    os.makedirs(os.path.join(OUT, 'scripts'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'listing'), exist_ok=True)
    rows, n_named, n_lua = [], 0, 0
    for h in w.entries:
        if h == MANIFEST:
            continue
        data = w.read(h)
        if not data or data[:4] != b'\x1bLua':
            continue
        n_lua += 1
        path = known.get(h)
        base = path.replace('/', '__') if path else f'_{h:016x}'
        n_named += path is not None
        f = os.path.join(OUT, 'scripts', base + '.luabin64')
        with open(f, 'wb') as fh:
            fh.write(data)
        rows.append(f'{h:016x}\t{path or ""}\t{len(data)}')
        if os.path.exists(LUAC):
            lst = subprocess.run([LUAC, '-l', '-l', '-p', f], capture_output=True, text=True, errors='replace').stdout
            with open(os.path.join(OUT, 'listing', base + '.txt'), 'w', encoding='utf-8') as fh:
                fh.write(lst)
    open(os.path.join(OUT, 'names.txt'), 'w').write('\n'.join(sorted(rows, key=lambda r: r.split('\t')[1])) + '\n')
    print(f'{n_lua} Lua scripts, {n_named} named -> {OUT}')


if __name__ == '__main__':
    main()
