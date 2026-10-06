"""Decodes a capture of tools/lol420_proxy.py: ENet (LENet Version.Patch420: 4-byte checksum, u8 session, u8 peer with
0x80 = a u16 sent time follows, big-endian commands), fragments put back together, Blowfish ECB (the key the client was
started with; a trailing part under 8 bytes is not encrypted; channel 0 = handshake is not encrypted), then the game
packet's id (u8, 0xFE = extended: u32 sender, u16 id; else u32 sender). Names from LeagueSandbox's LeaguePackets
GamePacketID enum (community names, used only as labels).

    python tools/lol420_decode.py <capture.bin> [--key 17BLOhi6KZsTtldTsizvHg==] [--out decoded.txt] [--hex 48]

Writes one line per game packet (time, direction, channel, id, name, sender net id, length, first bytes) and a summary
of counts per id and direction at the end.
"""
import argparse
import base64
import collections
import os
import re
import struct
import sys

from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
from cryptography.hazmat.primitives.ciphers import Cipher, modes

ENUM = r'C:\Users\Sorin\Desktop\4.20\GameServer\LeaguePackets\LeaguePackets\GamePacketID.cs'
CHANNELS = {0: 'handshake', 1: 'C2S', 2: 'synch', 3: 'broadcast', 4: 'broadcast_unrel', 5: 'chat', 6: 'quickchat', 7: 'loading'}
CMD_EXTRA = {1: 4, 2: 36, 3: 32, 4: 4, 5: 0, 6: 2, 7: 4, 8: 20, 9: 4, 10: 8, 11: 12}


def names():
    out = {}
    if os.path.exists(ENUM):
        for m in re.finditer(r'^\s*(\w+)\s*=\s*(0x[0-9A-Fa-f]+|\d+)', open(ENUM, encoding='utf-8-sig').read(), re.M):
            out[int(m.group(2), 0)] = m.group(1)
    return out


def records(path):
    b = open(path, 'rb').read()
    at = 0
    while at + 11 <= len(b):
        t, d, n = struct.unpack_from('<dBH', b, at)
        at += 11
        yield t, d, b[at:at + n]
        at += n


def commands(dg):
    """ENet commands of one datagram: (command, channel, flags, payload or None)."""
    if len(dg) < 6:
        return
    at = 4  # checksum
    at += 1  # session
    peer = dg[at]; at += 1
    if peer & 0x80:
        at += 2
    while at + 4 <= len(dg):
        cf, ch, seq = dg[at], dg[at + 1], struct.unpack_from('>H', dg, at + 2)[0]
        cmd = cf & 0x0F
        at += 4
        extra = CMD_EXTRA.get(cmd)
        if extra is None or at + extra > len(dg):
            return
        body = dg[at:at + extra]
        at += extra
        payload = None
        frag = None
        if cmd == 6:
            n = struct.unpack_from('>H', body, 0)[0]
        elif cmd in (7, 9):
            n = struct.unpack_from('>H', body, 2)[0]
        elif cmd == 8:
            start, n, count, number, total, off = struct.unpack('>HHIIII', body)
            frag = (start, count, number, total, off)
        else:
            n = 0
        if cmd in (6, 7, 8, 9):
            payload = dg[at:at + n]
            at += n
        yield cmd, ch, cf & 0xF0, payload, frag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('capture')
    ap.add_argument('--key', default='17BLOhi6KZsTtldTsizvHg==')
    ap.add_argument('--out', default=None)
    ap.add_argument('--hex', type=int, default=48)
    a = ap.parse_args()
    key = base64.b64decode(a.key)
    bf = Cipher(Blowfish(key), modes.ECB())
    ids = names()

    def decrypt(p):
        n = len(p) - len(p) % 8
        if n == 0:
            return p
        dec = bf.decryptor()
        return dec.update(p[:n]) + dec.finalize() + p[n:]

    frags = {}
    lines = []
    counts = collections.Counter()
    for t, d, dg in records(a.capture):
        for cmd, ch, flags, payload, frag in commands(dg):
            if payload is None:
                continue
            if frag:
                start, count, number, total, off = frag
                k = (d, ch, start)
                buf = frags.setdefault(k, [bytearray(total), set()])
                buf[0][off:off + len(payload)] = payload
                buf[1].add(number)
                if len(buf[1]) < count:
                    continue
                payload = bytes(buf[0])
                del frags[k]
            data = payload if ch == 0 else decrypt(payload)
            if not data:
                continue
            pid = data[0]
            sender = struct.unpack_from('<I', data, 1)[0] if len(data) >= 5 else 0
            if pid == 0xFE and len(data) >= 7:
                pid = struct.unpack_from('<H', data, 5)[0]
            name = ids.get(pid, '?')
            if ch == 0:
                name = 'KeyCheck'
            if ch == 7:
                name = 'loading:' + str(data[0])
            arrow = 'C->S' if d == 0 else 'S->C'
            counts[(arrow, pid, name)] += 1
            lines.append(f'{t:9.3f} {arrow} {CHANNELS.get(ch, ch):>10} {pid:#06x} {name:<40} net {sender:#010x} len {len(data):5d}  {data[:a.hex].hex(" ")}')
    out = a.out or os.path.splitext(a.capture)[0] + '.txt'
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        f.write('\n\n==== counts\n')
        for (arrow, pid, name), n in sorted(counts.items(), key=lambda kv: (kv[0][0], -kv[1])):
            f.write(f'{arrow} {pid:#06x} {name:<40} {n}\n')
    print(f'{len(lines)} game packets -> {out}')


if __name__ == '__main__':
    main()
