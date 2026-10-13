"""The 16.20 client's string table (Global.en_US.wad.client, data/menu/en_us/lol.stringtable): look keys up.

    python tools/rst16.py <key> [<key> ...]      the text of each key ('?' = no such key)
    python tools/rst16.py --find <text>          the hashes of the entries whose text contains <text>

Format (RST): 'RST', a version byte, u32 count, count x u64 (the key's hash in the low bits, the text's offset
above them), then the texts (zero-terminated UTF-8). The hash is xxh3-64 of the lower-cased key cut to 38 bits
(xxh64 and 40 bits in old versions): the number of bits is tried against a known key.
"""
import os
import struct
import sys

import xxhash

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import wad  # noqa: E402

WAD = os.path.join(HERE, '..', 'game16', 'DATA', 'FINAL', 'Localized', 'Global.en_US.wad.client')
PATH = 'data/menu/en_us/lol.stringtable'
KNOWN = 'game_announcement_OnFirstTowerKill_Friendly'
_table = None


def table():
    """({hash: text}, bits)"""
    global _table
    if _table is None:
        d = wad.read(WAD, PATH)
        if d[:3] != b'RST':
            raise ValueError('not a string table')
        version = d[3]
        at = 4
        if version in (2, 3):
            if d[at]:
                n = struct.unpack_from('<I', d, at + 1)[0]
                at += 5 + n
            else:
                at += 1
        count = struct.unpack_from('<I', d, at)[0]
        at += 4
        raw = struct.unpack_from(f'<{count}Q', d, at)
        at += 8 * count
        if version < 5:
            at += 1
        data = d[at:]
        best = None
        for bits in (38, 39, 40):
            mask = (1 << bits) - 1
            want = xxhash.xxh3_64(KNOWN.lower().encode()).intdigest() & mask
            if any((r & mask) == want for r in raw):
                best = bits
                break
        bits = best or 38
        mask = (1 << bits) - 1
        out = {}
        for r in raw:
            off = r >> bits
            end = data.find(b'\0', off)
            out[r & mask] = data[off:end].decode('utf-8', 'replace')
        _table = (out, bits)
    return _table


def text(key):
    t, bits = table()
    return t.get(xxhash.xxh3_64(key.lower().encode()).intdigest() & ((1 << bits) - 1))


if __name__ == '__main__':
    a = sys.argv[1:]
    t, bits = table()
    if a and a[0] == '--find':
        for h, s in t.items():
            if a[1].lower() in s.lower():
                print(f'{h:010x} {s[:160]}')
    else:
        print(len(t), 'entries,', bits, 'bit hashes')
        for k in a:
            print(k, '->', text(k) or '?')
