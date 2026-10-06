"""Riot's release manifests (RMAN v2) and their downloads, read here without third-party tools.

A manifest: "RMAN", u8 major, u8 minor, u16 flags, u32 body offset, u32 compressed size, u64 manifest id,
u32 uncompressed size; the body is one zstd frame holding a FlatBuffers table:
    0 bundles [Bundle{0 id u64, 1 chunks [Chunk{0 id u64, 1 compressed size u32, 2 uncompressed size u32}]}]
    1 languages [Language{0 id u8, 1 name}]
    2 files [File{0 id, 1 directory id, 2 size u32, 3 name, 4 language mask u64, 7 chunk ids [u64], 9 symlink}]
    3 directories [Directory{0 id, 1 parent id, 2 name}]
A file is its chunks in order; a chunk is a zstd frame stored in a bundle at <base>/bundles/<BUNDLE ID>.bundle, the
bundle's chunks laid one after the other in the order of its chunk list.

  rman.py list <manifest> [filter]            files with sizes (filter: substring of the path)
  rman.py size <manifest> [lang ...]          total size (files without a language + the given languages)
  rman.py get <manifest> <base url> <out dir> [lang ...]   download and assemble the files
"""
import os
import struct
import sys
import urllib.request

import zstandard


class FB:
    def __init__(self, buf):
        self.b = buf

    def u8(self, o): return self.b[o]
    def u16(self, o): return struct.unpack_from('<H', self.b, o)[0]
    def u32(self, o): return struct.unpack_from('<I', self.b, o)[0]
    def i32(self, o): return struct.unpack_from('<i', self.b, o)[0]
    def u64(self, o): return struct.unpack_from('<Q', self.b, o)[0]

    def root(self):
        return self.u32(0)

    def field(self, table, i):
        """absolute position of field i of a table, or None"""
        vt = table - self.i32(table)
        vsize = self.u16(vt)
        if 4 + 2 * i >= vsize:
            return None
        off = self.u16(vt + 4 + 2 * i)
        return table + off if off else None

    def ref(self, pos):
        return pos + self.u32(pos)

    def vector(self, table, i):
        p = self.field(table, i)
        if p is None:
            return []
        v = self.ref(p)
        n = self.u32(v)
        return [v + 4 + 4 * k for k in range(n)]

    def tables(self, table, i):
        return [self.ref(p) for p in self.vector(table, i)]

    def string(self, table, i):
        p = self.field(table, i)
        if p is None:
            return ''
        s = self.ref(p)
        n = self.u32(s)
        return self.b[s + 4:s + 4 + n].decode('utf-8', 'replace')

    def scalar(self, table, i, kind, default=0):
        p = self.field(table, i)
        if p is None:
            return default
        return {'u8': self.u8, 'u16': self.u16, 'u32': self.u32, 'u64': self.u64}[kind](p)

    def u64s(self, table, i):
        p = self.field(table, i)
        if p is None:
            return []
        v = self.ref(p)
        n = self.u32(v)
        return list(struct.unpack_from(f'<{n}Q', self.b, v + 4))


def load(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'RMAN', 'not a manifest'
    off, csize = struct.unpack_from('<II', d, 8)
    body = zstandard.ZstdDecompressor().decompress(d[off:off + csize], max_output_size=1 << 30)
    fb = FB(body)
    root = fb.root()
    chunks = {}
    for bt in fb.tables(root, 0):
        bid = fb.scalar(bt, 0, 'u64')
        at = 0
        for ct in fb.tables(bt, 1):
            cid = fb.scalar(ct, 0, 'u64')
            cs = fb.scalar(ct, 1, 'u32')
            us = fb.scalar(ct, 2, 'u32')
            chunks[cid] = (bid, at, cs, us)
            at += cs
    langs = {fb.scalar(t, 0, 'u8'): fb.string(t, 1) for t in fb.tables(root, 1)}
    dirs = {}
    for t in fb.tables(root, 3):
        dirs[fb.scalar(t, 0, 'u64')] = (fb.scalar(t, 1, 'u64'), fb.string(t, 2))

    def dirpath(i):
        parts = []
        while i in dirs and dirs[i][1]:
            parts.append(dirs[i][1])
            i = dirs[i][0]
        return '/'.join(reversed(parts))
    files = []
    for t in fb.tables(root, 2):
        name = fb.string(t, 3)
        d0 = dirpath(fb.scalar(t, 1, 'u64'))
        mask = fb.scalar(t, 4, 'u64')
        files.append({'path': (d0 + '/' if d0 else '') + name, 'size': fb.scalar(t, 2, 'u32'),
                      'langs': [langs.get(k + 1, str(k + 1)) for k in range(64) if mask >> k & 1],
                      'chunks': fb.u64s(t, 7), 'link': fb.string(t, 9)})
    return files, chunks, langs


def wanted(f, langs):
    return not f['langs'] or any(l in langs for l in f['langs'])


def get(path, base, out, langs):
    files, chunks, _ = load(path)
    todo = [f for f in files if wanted(f, langs) and not f['link']]
    # fetch whole bundles once each (a bundle may serve many files), keep the needed chunks in memory per bundle
    need = {}
    for f in todo:
        for c in f['chunks']:
            need.setdefault(chunks[c][0], set()).add(c)
    cache_dir = os.path.join(out, '.bundles')
    os.makedirs(cache_dir, exist_ok=True)
    total = sum(f['size'] for f in todo)
    print(f'{len(todo)} files, {total / 1e6:.1f} MB, {len(need)} bundles', flush=True)

    def fetch(bid):
        bp = os.path.join(cache_dir, f'{bid:016X}.bundle')
        if os.path.exists(bp):
            return 0
        url = f'{base}/bundles/{bid:016X}.bundle'
        for attempt in range(5):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'curl/8.4.0'}), timeout=120) as r:
                    blob = r.read()
                open(bp + '.part', 'wb').write(blob)
                os.replace(bp + '.part', bp)
                return len(blob)
            except Exception as e:
                err = e
        raise RuntimeError(f'{url}: {err}')
    from concurrent.futures import ThreadPoolExecutor
    got = 0
    with ThreadPoolExecutor(8) as ex:
        for k, n in enumerate(ex.map(fetch, sorted(need))):
            got += n
            if k % 100 == 0 or k == len(need) - 1:
                print(f'  bundles {k + 1}/{len(need)}, {got / 1e6:.0f} MB downloaded', flush=True)
    # assemble each file from its chunks, reading them straight out of the cached bundles
    dz = zstandard.ZstdDecompressor()
    for f in todo:
        p = os.path.join(out, f['path'])
        os.makedirs(os.path.dirname(p) or out, exist_ok=True)
        with open(p, 'wb') as fh:
            for c in f['chunks']:
                bid, at, cs, us = chunks[c]
                with open(os.path.join(cache_dir, f'{bid:016X}.bundle'), 'rb') as bf:
                    bf.seek(at)
                    fh.write(dz.decompress(bf.read(cs), max_output_size=us))
        if os.path.getsize(p) != f['size']:
            raise RuntimeError(f"{f['path']}: {os.path.getsize(p)} bytes, expected {f['size']}")
    print(f'done: {len(todo)} files, sizes checked', flush=True)


if __name__ == '__main__':
    cmd, man = sys.argv[1], sys.argv[2]
    if cmd == 'list':
        files, _, langs = load(man)
        flt = sys.argv[3] if len(sys.argv) > 3 else ''
        for f in sorted(files, key=lambda f: f['path']):
            if flt in f['path']:
                print(f"{f['size']:12} {f['path']} {','.join(f['langs'])} {('-> ' + f['link']) if f['link'] else ''}")
    elif cmd == 'size':
        files, _, langs = load(man)
        sel = sys.argv[3:]
        print('languages:', sorted(langs.values()))
        print(f"{sum(f['size'] for f in files if wanted(f, sel)) / 1e6:.1f} MB for {sel or 'no language'}; "
              f"all: {sum(f['size'] for f in files) / 1e6:.1f} MB, {len(files)} files")
    elif cmd == 'get':
        get(man, sys.argv[3], sys.argv[4], sys.argv[5:])
