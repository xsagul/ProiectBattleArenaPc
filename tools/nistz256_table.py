"""OpenSSL's ecp_nistz256_precomputed table, computed from the curve (no OpenSSL source needed).

The 13.3 client links OpenSSL's x86 assembly; ecp_nistz256-x86 puts a page-aligned table of 37 x 64 P-256 points
before its constants (RR = 3, 0, -1, -5, -2, -1, -3, 4 at rva 0x41000). Entry [i][j] = (j + 1) * 2^(7 i) * G as affine
(x, y), each 32 bytes little-endian in Montgomery form (value * 2^256 mod p): 37 * 64 * 64 = 151,552 bytes = the 37
pages at rva 0x1c000..0x41000, which the packer never serves in clear.

  nistz256_table.py write <out.bin>     the table's bytes
  nistz256_table.py compare             the table against the dump (and the keystream the packer would have needed)
"""
import os
import sys

P = 2**256 - 2**224 + 2**192 + 2**96 - 1
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
G = (0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296,
     0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5)
R = 2**256 % P


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    (x1, y1), (x2, y2) = a, b
    if x1 == x2:
        if (y1 + y2) % P == 0:
            return None
        l = (3 * x1 * x1 - 3) * pow(2 * y1, -1, P) % P
    else:
        l = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (l * l - x1 - x2) % P
    return x3, (l * (x1 - x3) - y1) % P


def table():
    out = bytearray()
    base = G
    for i in range(37):
        pt = None
        for j in range(64):
            pt = add(pt, base)
            out += (pt[0] * R % P).to_bytes(32, 'little') + (pt[1] * R % P).to_bytes(32, 'little')
        for _ in range(7):
            base = add(base, base)
    return bytes(out)


if __name__ == '__main__':
    t = table()
    if sys.argv[1] == 'write':
        open(sys.argv[2], 'wb').write(t)
        print(len(t), 'bytes')
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        mem = open(os.path.join(here, '..', 'client-src', 'exe_image_unpacked.bin'), 'rb').read()
        blk = mem[0x1c000:0x41000]
        print('table', len(t), 'bytes; equal to the dump:', t == blk,
              '; equal bytes:', sum(1 for a, b in zip(t, blk) if a == b), 'of', len(t))
        print('table starts', t[:32].hex())
        print('dump starts ', blk[:32].hex())
