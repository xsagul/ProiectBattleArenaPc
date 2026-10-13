"""ROFL version 2 (16.20) container: header, then records [u32 id][u32 next][u8 type][u32 length][u32 packed length]
+ one zstd frame each; JSON metadata at the end of the file. No encryption (measured on EUN1-4013530370.rofl).

  rofl2.py <file.rofl> summary        records, block counts, packet ids by frequency
  rofl2.py <file.rofl> first <n>      the first n blocks in stream order
"""
import collections, json, struct, sys
import zstandard
def blocks(buf):
    """(time, channel, packet id, object id, body) for each block of a record. As on 13.3 (rofl_packets.blocks) but for
    the object id's short form: the byte is a signed difference from the previous block's id [measured: with an
    unsigned one the three packets that follow every minion spawn came out as about "minion id + 0x100"]."""
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
            obj = (obj + struct.unpack_from('<b', buf, at)[0]) & 0xffffffff
            at += 1
        else:
            obj = struct.unpack_from('<I', buf, at)[0]
            at += 4
        if at + length > n:
            raise ValueError('block of %d bytes at %d runs past the record (%d)' % (length, at, n))
        yield t, marker & 0x0F, pid, obj, buf[at:at + length]
        at += length


ZSTD = bytes.fromhex('28b52ffd')


class Rofl2:
    def __init__(self, path):
        d = self.data = open(path, 'rb').read()
        assert d[:6] == b'RIOT\x02\x00', 'not a ROFL v2 file'
        self.protocol = d[6:14]
        n = d[14]
        self.version = d[15:15 + n].decode()
        at = 15 + n
        self.records = []
        dec = zstandard.ZstdDecompressor()
        while d[at + 17:at + 21] == ZSTD:
            rid, nxt, typ, length, packed = struct.unpack_from('<IIBII', d, at)
            self.records.append({'id': rid, 'next': nxt, 'type': typ, 'length': length, 'at': at + 17, 'packed': packed})
            at += 17 + packed
            if d[at + 17:at + 21] != ZSTD:      # something sits between two records (34 bytes after the first one)
                skip = d.find(ZSTD, at) - 17 - at
                if 0 < skip < 4096:
                    self.records[-1]['gap'] = d[at:at + skip]
                    at += skip
        self.end = at
        self._dec = dec

    def payload(self, r):
        return self._dec.decompress(self.data[r['at']:r['at'] + r['packed']], max_output_size=r['length'] + 16)


def stream(r, kinds=(1,)):
    for e in r.records:
        if e['type'] in kinds:
            for b in blocks(r.payload(e)):
                yield e, b


if __name__ == '__main__':
    r = Rofl2(sys.argv[1])
    if sys.argv[2] == 'summary':
        print('protocol', r.protocol.hex(), 'version', r.version, 'records', len(r.records), 'data ends at', r.end, 'of', len(r.data))
        types = collections.Counter(e['type'] for e in r.records)
        print('record types', dict(types), 'gaps', [(e['id'], len(e['gap'])) for e in r.records if 'gap' in e])
        ids, n, bad = collections.Counter(), 0, 0
        for e in r.records:
            buf = r.payload(e)
            assert len(buf) == e['length'], (e, len(buf))
            try:
                for t, ch, pid, obj, body in blocks(buf):
                    n += 1
                    if e['type'] == 1:
                        ids[pid] += 1
            except Exception as x:
                bad += 1
                print('record', e['id'], 'type', e['type'], 'does not parse as blocks:', x)
        print('blocks', n, 'records that do not parse', bad, 'distinct packet ids in chunks', len(ids))
        print('most frequent', ids.most_common(25))
    else:
        for k, (e, (t, ch, pid, obj, body)) in enumerate(stream(r, kinds=(1, 2, 3))):
            if k >= int(sys.argv[3]):
                break
            print(f'rec {e["id"]:3} type {e["type"]} t {t:9.3f} ch {ch} id {pid:5} obj {obj:08x} len {len(body):5} {body[:24].hex()}')
