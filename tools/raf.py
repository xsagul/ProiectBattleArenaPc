"""Riot Archive Files (.raf + .raf.dat), the game client's archives up to 2016 (e.g. patch 4.20). Reads only.

Index (.raf), little-endian: u32 magic 0x18BE0EF0, u32 version, u32 manager index, u32 file list offset,
u32 path list offset. File list: u32 count, then count x (u32 path hash, u32 data offset, u32 data size,
u32 path index). Path list: u32 size, u32 count, then count x (u32 string offset, u32 string length); the strings'
offsets count from the start of the path list. Each entry's bytes in the .raf.dat are zlib-compressed (most of them)
or stored as they are.

  python tools/raf.py list <folder with .raf files> [substring]
  python tools/raf.py get <folder> <path inside the archives> <out file>
"""
import os
import struct
import sys
import zlib


def read_index(path):
    data = open(path, 'rb').read()
    magic, version, manager, files_off, paths_off = struct.unpack_from('<5I', data, 0)
    if magic != 0x18BE0EF0:
        raise ValueError('not a RAF index: ' + path)
    _, count = struct.unpack_from('<2I', data, paths_off)
    paths = []
    for i in range(count):
        off, length = struct.unpack_from('<2I', data, paths_off + 8 + i * 8)
        paths.append(data[paths_off + off:paths_off + off + length].rstrip(b'\0').decode('latin-1'))
    (n,) = struct.unpack_from('<I', data, files_off)
    entries = []
    for i in range(n):
        h, off, size, pi = struct.unpack_from('<4I', data, files_off + 4 + i * 16)
        entries.append((paths[pi], off, size))
    return entries


def archives(folder):
    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith('.raf'):
                yield os.path.join(root, f)


def entry_bytes(raf_path, off, size):
    with open(raf_path + '.dat', 'rb') as f:
        f.seek(off)
        raw = f.read(size)
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return raw


def main():
    cmd, folder = sys.argv[1], sys.argv[2]
    if cmd == 'list':
        sub = sys.argv[3].lower() if len(sys.argv) > 3 else ''
        for raf in archives(folder):
            for path, off, size in read_index(raf):
                if sub in path.lower():
                    print(path, size, os.path.relpath(raf, folder))
    elif cmd == 'get':
        want = sys.argv[3].lower()
        found = None
        for raf in archives(folder):  # the newest release holds the latest copy: keep the last match
            for path, off, size in read_index(raf):
                if path.lower() == want:
                    found = (raf, off, size)
        if not found:
            sys.exit('not found: ' + want)
        open(sys.argv[4], 'wb').write(entry_bytes(*found))


if __name__ == '__main__':
    main()
