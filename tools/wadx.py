import struct, zlib, zstandard, sys, os

class Wad:
    def __init__(self, path):
        self.f = open(path, 'rb')
        d = self.f.read(272)
        assert d[:2] == b'RW', d[:4]
        self.major = d[2]
        if self.major == 3:
            self.f.seek(268)
            n = struct.unpack('<I', self.f.read(4))[0]
        else:
            self.f.seek(4); n = struct.unpack('<I', self.f.read(4))[0]
        self.entries = {}
        for _ in range(n):
            h, off, cs, us, t, dup, sc, sha = struct.unpack('<QIIIBBHQ', self.f.read(32))
            self.entries[h] = (off, cs, us, t, sc)
    def read(self, h):
        off, cs, us, t, sc = self.entries[h]
        self.f.seek(off)
        raw = self.f.read(cs)
        t &= 0xf
        if t == 0: return raw
        if t == 1: return zlib.decompress(raw, 31)
        if t == 3 or t == 4:
            import io
            return zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw), read_across_frames=True).read()
        if t == 2:
            return None
        raise ValueError(t)
