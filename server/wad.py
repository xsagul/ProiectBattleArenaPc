"""Files out of a .wad.client archive of game16, and Riot's TEX textures as images.

    wad.read(wad path, 'assets/characters/ahri/hud/ahri_square.tex')   by path (hashed with xxhash64, lower case)
    wad.read(wad path, 0xd4f389b247cca735)                             by the 64-bit hash a bin names a file with
    wad.texture(data) -> PIL image of a TEX (DXT1 / DXT5 / BGRA8; the largest mip)

Archive format (v3): the entry count at 0x10c, then 32-byte entries (u64 path hash, u32 offset, u32 packed size,
u32 size, u8 kind in the low nibble: 0 plain, 3 zstd, 4 zstd in several frames).
"""
import io
import struct

_toc = {}


def toc(path):
    if path not in _toc:
        with open(path, 'rb') as f:
            head = f.read(0x110)
            n = struct.unpack_from('<I', head, 0x10c)[0]
            raw = f.read(32 * n)
        _toc[path] = {struct.unpack_from('<Q', raw, i * 32)[0]: struct.unpack_from('<IIIB', raw, i * 32 + 8) for i in range(n)}
    return _toc[path]


def read(path, name):
    import xxhash
    import zstandard
    h = name if isinstance(name, int) else xxhash.xxh64(name.lower().encode()).intdigest()
    e = toc(path).get(h)
    if e is None:
        return None
    off, csize, usize, kind = e
    with open(path, 'rb') as f:
        f.seek(off)
        raw = f.read(csize)
    kind &= 0x0f
    if kind == 0:
        return raw
    if kind in (3, 4):
        try:
            return zstandard.ZstdDecompressor().decompress(raw, max_output_size=usize)
        except zstandard.ZstdError:
            # several frames one after the other (kind 4): each has its own header, some pieces are stored plain
            out, at = b'', 0
            d = zstandard.ZstdDecompressor()
            while at < len(raw) and len(out) < usize:
                if raw[at:at + 4] == b'\x28\xb5\x2f\xfd':
                    obj = d.decompressobj()
                    out += obj.decompress(raw[at:])
                    at = len(raw) - len(obj.unused_data)
                else:
                    out += raw[at:]
                    break
            return out[:usize]
    return None


def texture(data):
    """a TEX file -> PIL image"""
    from PIL import Image
    if data is None or data[:4] != b'TEX\0':
        return None
    w, h = struct.unpack_from('<HH', data, 4)
    fmt, mips = data[9], data[11] & 1
    body = data[12:]
    blocks = max(1, (w + 3) // 4) * max(1, (h + 3) // 4)
    if fmt in (10, 12):
        size = blocks * (8 if fmt == 10 else 16)
        top = body[-size:] if mips else body[:size]            # with mips the largest picture is the last
        four = b'DXT1' if fmt == 10 else b'DXT5'
        pf = struct.pack('<II4sIIIII', 32, 0x4, four, 0, 0, 0, 0, 0)
        head = b'DDS ' + struct.pack('<IIIIIII', 124, 0x81007, h, w, size, 0, 0) + bytes(44) + pf + struct.pack('<IIIII', 0x1000, 0, 0, 0, 0)
        return Image.open(io.BytesIO(head + top)).convert('RGBA')
    if fmt == 20:
        size = w * h * 4
        top = body[-size:] if mips else body[:size]
        return Image.frombuffer('RGBA', (w, h), top, 'raw', 'BGRA', 0, 1)
    return None


if __name__ == '__main__':
    import sys
    d = read(sys.argv[1], int(sys.argv[2], 16) if sys.argv[2].startswith('0x') else sys.argv[2])
    print(None if d is None else (len(d), d[:16]))
    if d and d[:4] == b'TEX\0' and len(sys.argv) > 3:
        texture(d).save(sys.argv[3])
