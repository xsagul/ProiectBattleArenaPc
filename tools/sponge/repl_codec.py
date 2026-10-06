"""Packet 595 (replication) written by our server, values by name.

Wire: the packet object (reader rva 0x8559c0) learnt by pkt_schema.py (research/exe133/codec/595.tree.json):
  +0xc  the buffer (a text field: one byte table, the bytes written last first)
  +0x18 the number of units in the buffer
  +0x1c a game time (float; 23.02 in the replay's first 595)
  +0x20 a counter (452 there)
The buffer, unit after unit (replication.py): u8 primary mask (one bit per group), u32 net id, then per group u32
secondary mask (one bit per value), u8 size, the values low bit first. A value is a float (4 bytes; 0 = 0xff alone;
a float whose first byte is 0xfe / 0xff gets 0xfe in front) or a packed int (7 bits a byte, low first).

Which value a (group, bit) is: the class's registration (repl_names.py -> research/exe133/repl_names.json). Hero
(registered in rva 0x17a490): group 0 mGold, mGoldTotal, ..., group 5 mHP, mMaxHP, ..., mPAR (mana), mExp, ...
Float or int: the register function's flag, kept as a bit mask at +4 of each group table (1 = float).

  repl_codec.py show            the hero's values by name, with their kind
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exe_dis as E  # noqa: E402

RES = os.path.join(HERE, '..', '..', 'research', 'exe133')
HERO = 'hero'


def classes():
    """{class key: {name: (group, bit, 'f' | 'i')}}"""
    d = json.load(open(os.path.join(RES, 'repl_names.json')))
    out = {}
    for key, c in d.items():
        names = {}
        for g, vals in c['values'].items():
            flags = c['flags'][int(g)]
            for v in vals:
                names[v['name']] = (int(g), v['bit'], 'f' if flags >> v['bit'] & 1 else 'i')
        out[key] = names
    return out


_cls = None


def names(cls=HERO):
    global _cls
    if _cls is None:
        _cls = classes()
    return _cls[cls]


def enc_value(kind, v):
    if kind == 'f':
        if v == 0:
            return b'\xff'
        raw = struct.pack('<f', v)
        return (b'\xfe' + raw) if raw[0] in (0xfe, 0xff) else raw
    v = int(v)
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def unit(net, values, cls=HERO):
    """one unit of a replication buffer: values {name: number}"""
    table = names(cls)
    groups = {}
    for name, v in values.items():
        g, b, kind = table[name]
        groups.setdefault(g, {})[b] = enc_value(kind, v)
    primary = 0
    out = b''
    for g in sorted(groups):
        primary |= 1 << g
        mask = sum(1 << b for b in groups[g])
        data = b''.join(groups[g][b] for b in sorted(groups[g]))
        out += struct.pack('<IB', mask, len(data)) + data
    return bytes([primary]) + struct.pack('<I', net) + out


_sc = None


def packet(units, game_time=0.0, counter=0):
    """units: [(net id, {name: number}, class key)] -> body of packet 595 (after [u16 id][u32 net id = 0])"""
    global _sc
    import pkt_schema as S
    if _sc is None:
        _sc = S.Schema.load(595)
    buf = b''.join(unit(n, v, c) for n, v, c in units)
    value = {'+0xc': {'text': buf.hex()}, '+0x18': f'{len(units):02x}',
             '+0x1c': struct.pack('<f', game_time).hex(), '+0x20': struct.pack('<I', counter).hex()}
    return _sc.encode(value)


def read(body):
    """body -> [(net id, {(group, bit): raw bytes})] through Riot's reader (emulator) and replication.parse"""
    import pkt_schema as S
    import pkt_tree as PT
    import replication as RP
    sc = S.Schema.load(595)
    T = read.__dict__.setdefault('T', PT.Tree(595))
    v = S.decode(T, sc, struct.pack('<HI', 595, 0) + body)
    if v is None:
        return None
    return v, RP.parse(bytes.fromhex(v['+0xc']['text']))


if __name__ == '__main__':
    if sys.argv[1] == 'show':
        for name, (g, b, k) in sorted(names().items(), key=lambda kv: kv[1]):
            print(f'group {g} bit {b:2d} {k} {name}')
