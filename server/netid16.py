"""The net id of a 16.20 packet on the wire (reader rva 0x11c4b80): a 7-bit varint, low part first, top bit = more
bytes follow; each byte is substituted through the 256-byte table at rva 0x1b1c720:
    value byte = T[(T[rol8((T[~b] + 0x54) & 255, 1)] - 0x4c) & 255]
The value is the net id with bit 30 flipped, except when its low 24 bits are zero (then it is the net id itself).

  netid16.py make      writes data/exe1620/netid_table.bin from the image
  netid16.py check     encodes sample ids and reads them back with the client's own reader (emu16)
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = os.path.join(HERE, '..', 'data', 'exe1620', 'netid_table.bin')
TABLE_RVA = 0x1b1c720


def _tables():
    t = open(TABLE, 'rb').read()
    rol = lambda x: ((x << 1) | (x >> 7)) & 255
    dec = bytes(t[(t[rol((t[~b & 255] + 0x54) & 255)] - 0x4c) & 255] for b in range(256))
    enc = bytearray(256)
    for b, v in enumerate(dec):
        enc[v] = b
    assert len(set(dec)) == 256
    return dec, bytes(enc)


DEC, ENC = _tables() if os.path.exists(TABLE) else (None, None)


def encode(netid):
    v = netid if netid & 0xffffff == 0 else netid ^ 0x40000000
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        out.append(ENC[b | (0x80 if v else 0)])
        if not v:
            return bytes(out)


def decode(data):
    """(net id, bytes used)"""
    v = shift = 0
    for i, b in enumerate(data):
        d = DEC[b]
        v |= (d & 0x7f) << shift
        shift += 7
        if not d & 0x80:
            v &= 0xffffffff
            return (v if v & 0xffffff == 0 else v ^ 0x40000000), i + 1
    raise ValueError('net id runs past the data')


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        img = open(os.path.join(HERE, '..', 'data', 'exe1620', 'exe_image_t0.bin'), 'rb').read()
        open(TABLE, 'wb').write(img[TABLE_RVA:TABLE_RVA + 256])
        print('table written')
    else:
        import emu16
        e = emu16.Emu()
        ok = 0
        ids = [0, 0x40000001, 0x4000007f, 0x40000080, 0x400000ae, 0x40001d93, 0x40123456, 0xff000000, 0x00000005, 0x4fffffff]
        for nid in ids:
            wire = encode(nid) + bytes.fromhex('d1f4')
            obj, used, ans = e.read_packet(1080, wire)
            got = struct.unpack('<I', e.mu.mem_read(obj + 0xc, 4))[0]
            ok += got == nid and ans == 1 and used == len(wire) and decode(wire)[0] == nid
            print(f'{nid:08x} -> {encode(nid).hex():10} client reads {got:08x} answer {ans}')
        print(f'{ok} of {len(ids)} identical')
