"""The network sponge: what Riot's server sent, straight from a .rofl replay (ROFL v1, patches up to 14.8).

A replay is the server's own packet stream as a spectator received it, cut into chunks (and keyframes: full states to
start from when seeking). The container is public knowledge: Blowfish-ECB with a key that is itself encrypted with the
game id, then gzip. Inside each chunk the packets follow one another as blocks:

    marker u8: low 4 bits channel; 0x80 time is a u8 of milliseconds since the last block (else a float32, seconds);
               0x10 length is a u8 (else u32); 0x40 same packet id as the last block (else u16);
               0x20 the object id is the last one plus a u8 (else u32)
    then `length` bytes: the packet's body

The packet ids and the bodies' field layouts are scrambled anew by Riot for every patch; this tool does not undo that.
It gives the stream's shape: which packet ids exist, how many, how large, how often, about which objects, in what order.

    python tools/sponge/rofl_packets.py <file.rofl> summary
    python tools/sponge/rofl_packets.py <file.rofl> dump <out.jsonl> [chunks|keyframes|all]
    python tools/sponge/rofl_packets.py <file.rofl> window <t0> <t1> [packet id]
"""
import base64
import collections
import gzip
import json
import struct
import sys

from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish
from cryptography.hazmat.primitives.ciphers import Cipher, modes


def bf_decrypt(key, data):
    d = Cipher(Blowfish(key), modes.ECB()).decryptor()
    out = d.update(data) + d.finalize()
    pad = out[-1]
    return out[:-pad] if 1 <= pad <= 8 else out


class Rofl:
    def __init__(self, path):
        self.data = open(path, 'rb').read()
        d = self.data
        assert d[:4] == b'RIOT', 'not a ROFL v1 file'
        (self.header_len, self.file_len, self.meta_off, self.meta_len, self.ph_off, self.ph_len, self.payload_off) = struct.unpack_from('<HIIIIII', d, 262)
        self.meta = json.loads(d[self.meta_off:self.meta_off + self.meta_len].decode('utf-8', 'replace'))
        (self.game_id, self.game_len, self.n_key, self.n_chunk, self.end_startup, self.start_game, self.key_interval, klen) = struct.unpack_from('<QIIIIIIH', d, self.ph_off)
        enc_key = d[self.ph_off + 34:self.ph_off + 34 + klen]
        self.chunk_key = bf_decrypt(str(self.game_id).encode(), base64.b64decode(enc_key))
        self.entries = []
        n = self.n_chunk + self.n_key
        base = self.payload_off + 17 * n
        for i in range(n):
            cid, typ, length, nxt, off = struct.unpack_from('<IBIII', d, self.payload_off + 17 * i)
            self.entries.append({'id': cid, 'type': typ, 'length': length, 'next': nxt, 'at': base + off})

    def payload(self, e):
        raw = self.data[e['at']:e['at'] + e['length']]
        return gzip.decompress(bf_decrypt(self.chunk_key, raw))


def blocks(buf):
    """(time, channel, packet id, object id, body) for each block of a decompressed chunk; raises when it does not fit."""
    at, t, pid, obj = 0, 0.0, 0, 0
    n = len(buf)
    while at < n:
        marker = buf[at]
        at += 1
        if marker & 0x80:
            t += buf[at] / 1000.0
            at += 1
        else:
            t = struct.unpack_from('<f', buf, at)[0]
            at += 4
        if marker & 0x10:
            length = buf[at]
            at += 1
        else:
            length = struct.unpack_from('<I', buf, at)[0]
            at += 4
        if not marker & 0x40:
            pid = struct.unpack_from('<H', buf, at)[0]
            at += 2
        if marker & 0x20:
            obj += buf[at]
            at += 1
        else:
            obj = struct.unpack_from('<I', buf, at)[0]
            at += 4
        if at + length > n:
            raise ValueError('block of %d bytes at %d runs past the chunk (%d)' % (length, at, n))
        yield t, marker & 0x0F, pid, obj, buf[at:at + length]
        at += length


def stream(r, kinds=(1,)):
    for e in r.entries:
        if e['type'] not in kinds:
            continue
        buf = r.payload(e)
        for b in blocks(buf):
            yield e, b


def main():
    r = Rofl(sys.argv[1])
    cmd = sys.argv[2] if len(sys.argv) > 2 else 'summary'
    if cmd == 'summary':
        print('game %d, version %s, %.1f s; %d chunks, %d keyframes (every %d s); startup ends at chunk %d, game starts at chunk %d' % (
            r.game_id, r.meta.get('gameVersion'), r.game_len / 1000.0, r.n_chunk, r.n_key, r.key_interval, r.end_startup, r.start_game))
        count, size, objs, first, last, chans = collections.Counter(), collections.Counter(), collections.defaultdict(set), {}, {}, collections.defaultdict(set)
        total = bad = 0
        for e in r.entries:
            if e['type'] != 1:
                continue
            try:
                for t, ch, pid, obj, body in blocks(r.payload(e)):
                    total += 1
                    count[pid] += 1
                    size[pid] += len(body)
                    if len(objs[pid]) < 5000:
                        objs[pid].add(obj)
                    first.setdefault(pid, t)
                    last[pid] = t
                    chans[pid].add(ch)
            except Exception as ex:  # noqa: BLE001
                bad += 1
                print('chunk %d: %s' % (e['id'], ex))
        print('%d packets of %d kinds in the chunks (%d chunks did not parse)' % (total, len(count), bad))
        print('%6s %8s %8s %7s %9s %9s  %s' % ('id', 'count', 'bytes', 'avg', 'first s', 'last s', 'objects, channels'))
        for pid, c in count.most_common():
            print('%6d %8d %8d %7.1f %9.1f %9.1f  %d%s, ch %s' % (pid, c, size[pid], size[pid] / c, first[pid], last[pid], len(objs[pid]),
                                                              '+' if len(objs[pid]) >= 5000 else '', ','.join(str(x) for x in sorted(chans[pid]))))
    elif cmd == 'dump':
        kinds = {'chunks': (1,), 'keyframes': (2,), 'all': (1, 2)}[sys.argv[4] if len(sys.argv) > 4 else 'chunks']
        n = 0
        with open(sys.argv[3], 'w') as f:
            for e, (t, ch, pid, obj, body) in stream(r, kinds):
                f.write(json.dumps({'chunk': e['id'], 'kind': e['type'], 't': round(t, 4), 'ch': ch, 'id': pid, 'obj': obj, 'hex': body.hex()}) + '\n')
                n += 1
        print(n, 'packets written')
    elif cmd == 'window':
        t0, t1 = float(sys.argv[3]), float(sys.argv[4])
        only = int(sys.argv[5]) if len(sys.argv) > 5 else None
        for e, (t, ch, pid, obj, body) in stream(r):
            if t0 <= t <= t1 and (only is None or pid == only):
                print('%9.3f ch %d id %5d obj %08x %4d bytes  %s' % (t, ch, pid, obj, len(body), body[:40].hex()))


if __name__ == '__main__':
    main()
