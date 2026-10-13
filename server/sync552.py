"""The movement packet's (552) sequence number: a header value the client checks per unit.

Measured in the client (13.3): the 552 handler (rva 0x29d4f0) passes the packet's +0xc to rva 0x19e900 for every
unit of the packet, which keeps the unit's last value at component +0x41c and REJECTS a path whose value is smaller
(accepts >=, or a wrap of more than 0x3fffffff). In clear (the handler's own decode at rva 0x29d5c4: xor 0x64, table
rva 0x156ffb8, xor 0x2f, bit reversal, xor 0xf7) the value is a server-wide count of movement updates: 493 at 0.1 s,
282,287 at 168 s, 1,476,401 at 679 s of the replay -- not a time.

The header's own byte coding is not learnt yet (its first byte picks the coding of the rest), so our server takes the
replay's own headers, sorted by their value, as an increasing sequence: each 552 we send gets the next one, which is
what the client needs (every new path of a unit carries a value >= its last).

  sync552.py        builds data/exe133/s2c_552_sync_heads.json ([[value, head hex], ...] sorted)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'exe133', 's2c_552_sync_heads.json')
_heads = None
_next = [0]


def value_of(obj_bytes):
    import packet_emu as P
    T = P.IMG[0x156ffb8:0x156ffb8 + 256]

    def rev(c):
        edx = ((c * 0x802) & 0x22110) | ((c * 0x8020) & 0x88440)
        return ((edx * 0x10101) >> 16) & 0xff
    return struct.unpack('<I', bytes(rev(T[b ^ 0x64] ^ 0x2f) ^ 0xf7 for b in obj_bytes[0xc:0x10]))[0]


def build():
    sys.path.insert(0, HERE)
    import packet_emu as P
    import lol_packets as LP
    t = P.table()
    emu = P.Emu()
    seen = {}
    for tm, ch, p, obj, body in P.packets(P.ROFL, 552):
        s = LP.split_552(body)
        if not s:
            continue
        ok, left, o = emu.deserialize(t[552], 552, obj, body)
        if o:
            seen.setdefault(value_of(o), s[0].hex())
    heads = sorted([v, h] for v, h in seen.items())
    json.dump(heads, open(OUT, 'w'))
    print(len(heads), 'headers, values', heads[0][0], '..', heads[-1][0])
    return heads


PARTS = os.path.join(HERE, '..', 'data', 'exe133', 's2c_552_head_parts.json')
MAX_ENTRIES = 18          # the largest movement group of the replay; we never write a larger one
_parts = None
_last = [None]


def build_parts():
    """The header in parts (2026-10-11). Its first byte: the low nibble is 8 plus two bits that vary freely, the high
    nibble says how many units the packet moves: 0 = one, 5 = two, 1 / 2 / 4 / 7 = a count byte follows (3 .. 18 in
    the replay, one byte per count, the same for the four nibbles). Then the sequence value, 2 to 4 bytes by its size
    (one coding for every count). The client moves ONLY as many units as the header says: our packets used to borrow
    a replay header whole, whatever its count -- of nine champions sent off in one packet two walked, of a wave's
    minions the first one or two got their next path and the rest stood until a later packet named them first.
    Built headers were read back through Riot's reader for counts 1, 2, 3, 4, 5, 9, 17: value and count as meant."""
    import collections
    sys.path.insert(0, HERE)
    import lol_packets as LP
    import rofl_packets as R
    import waypoints as Wp
    val = {h: v for v, h in json.load(open(OUT))}
    count_byte, tails = collections.defaultdict(collections.Counter), {}
    for e, (t, ch, pid, obj, body) in R.stream(R.Rofl(os.path.join(HERE, '..', 'data', 'rofl', 'KR-6363178603_13.3.rofl'))):
        if pid != 552:
            continue
        s = LP.split_552(body)
        if not s:
            continue
        try:
            n = len(Wp.parse(s[1]))
        except Exception:
            continue
        h = s[0]
        if n >= 3:
            count_byte[n][h[1]] += 1
        v = val.get(h.hex())
        if v is not None:
            tails.setdefault(v, (h[2:] if n >= 3 else h[1:]).hex())
    json.dump(dict(count_byte={n: c.most_common(1)[0][0] for n, c in count_byte.items()}, tails=sorted(tails.items())),
              open(PARTS, 'w'))
    print(len(tails), 'values, counts', sorted(count_byte))


def next_head(at_least=0, count=1):
    """the header of our next movement packet (bytes) for `count` units, its value >= at_least and >= every one
    given before (the client takes a unit's path when the value is not below the unit's last one)"""
    global _parts
    if _parts is None:
        d = json.load(open(PARTS))
        _parts = ({int(k): v for k, v in d['count_byte'].items()}, d['tails'])
    count_byte, tails = _parts
    i = _next[0]
    while i < len(tails) - 1 and tails[i][0] < at_least:
        i += 1
    _next[0] = min(i + 1, len(tails) - 1)
    _last[0] = tails[i][0]
    tail = bytes.fromhex(tails[i][1])
    if count == 1:
        return bytes([0x08]) + tail, tails[i][0]
    if count == 2:
        return bytes([0x58]) + tail, tails[i][0]
    if count not in count_byte:
        raise ValueError(f'no movement header for {count} units (1 .. {MAX_ENTRIES})')
    return bytes([0x28, count_byte[count]]) + tail, tails[i][0]


def last_value(default=0):
    """the value of the header given out last (what the client has seen as the newest movement), or default"""
    return default if _last[0] is None else _last[0]


if __name__ == '__main__':
    if sys.argv[1:] == ['parts']:
        build_parts()
    else:
        build()
