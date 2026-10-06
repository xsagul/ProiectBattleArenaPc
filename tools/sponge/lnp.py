"""The 13.3 client's transport ("LNP"), as read from the client's own send path (rva 0x2ef8e0 send thread,
0x2efe50 writes one message, 0x2de720 its checksum, 0x9c4f80 the cipher).

A datagram on the wire:
  [u32 a][u32 b]       only when the connection has a 64-bit id (the client's hello has one)
  then, encrypted:
  u16  sequence / flags word (message +8); when its top bit is set an extra u64 follows the flag byte
  u32  checksum, big-endian: CRC-32 (polynomial 0x04C11DB7, not reflected, start 0xFFFFFFFF, inverted at the end)
       over: the u16 above (low byte first), 8 bytes of the message's peer id, 8 bytes of message +0x20, payload
  u8   flag (message +0x40 != 0)
  [u64 message +0x20]  only when the u16's top bit is set
  payload

Encryption (only when the connection has a key for the message's peer id): Blowfish in CFB mode over the whole 8-byte
blocks (a tail shorter than 8 stays as it is), starting each time from the same chain value; then the bytes are put
in reverse order; then the same CFB pass again.

  lnp.py open <key base64> <capture.txt | ba_net.log>     decrypt every datagram of a capture and check its checksum
"""
import base64, struct, sys
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
from cryptography.hazmat.primitives.ciphers import Cipher, modes


def _crc_table():
    t = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
        t.append(c)
    return t


CRC = _crc_table()


def crc_feed(c, data):
    # the client's form: the next byte is shifted in at the bottom (so the last four bytes are not "flushed")
    for b in data:
        c = (((c << 8) & 0xFFFFFFFF) | b) ^ CRC[c >> 24]
    return c


class Lnp:
    def __init__(self, key, chain=bytes(8)):
        self.key, self.chain = key, chain

    def _cfb(self, data, enc):
        n = len(data) & ~7
        c = Cipher(Blowfish(self.key), modes.CFB(self.chain))
        x = c.encryptor() if enc else c.decryptor()
        return x.update(bytes(data[:n])) + bytes(data[n:])

    def seal(self, body):
        return self._cfb(self._cfb(body, True)[::-1], True)

    def open(self, body):
        return self._cfb(self._cfb(body, False)[::-1], False)


def checksum(seq, peer, extra, payload):
    c = crc_feed(0xFFFFFFFF, struct.pack('<H', seq))
    c = crc_feed(c, struct.pack('<Q', peer))
    c = crc_feed(c, struct.pack('<Q', extra))
    c = crc_feed(c, payload)
    return c ^ 0xFFFFFFFF


def parse(body):
    """Decrypted body -> dict."""
    seq, crc, flag = struct.unpack_from('<H', body)[0], struct.unpack_from('>I', body, 2)[0], body[6]
    off, extra = 7, None
    if seq & 0x8000:
        extra = struct.unpack_from('<Q', body, 7)[0]; off = 15
    return dict(seq=seq, crc=crc, flag=flag, extra=extra, payload=body[off:])


if __name__ == '__main__':
    if sys.argv[1] == 'open':
        lnp = Lnp(base64.b64decode(sys.argv[2]))
        seen = {}
        for line in open(sys.argv[3]):
            w = line.split()
            if ' bytes ' in line and 'udp from' in line:
                d = bytes.fromhex(w[-1])
            else:
                continue
            seen[d] = seen.get(d, 0) + 1
        for d, n in seen.items():
            m = parse(lnp.open(d[8:]))
            oks = [f'peer={p} extra={e:#x}' for p in (0, 1) for e in (0, 0xFFFFFFFFFFFFFFFF)
                   if checksum(m['seq'], p, e, m['payload']) == m['crc']]
            print(f'{n:4} x  id {d[:8].hex()}  seq {m["seq"]:#06x}  crc {m["crc"]:08x} {"ok " + oks[0] if oks else "MISMATCH"}  flag {m["flag"]}'
                  f'  payload {len(m["payload"])}: {m["payload"][:40].hex()}')
