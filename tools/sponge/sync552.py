"""The movement packet's (552) sequence number: a header value the client checks per unit.

Measured in the client (13.3): the 552 handler (rva 0x29d4f0) passes the packet's +0xc to rva 0x19e900 for every
unit of the packet, which keeps the unit's last value at component +0x41c and REJECTS a path whose value is smaller
(accepts >=, or a wrap of more than 0x3fffffff). In clear (the handler's own decode at rva 0x29d5c4: xor 0x64, table
rva 0x156ffb8, xor 0x2f, bit reversal, xor 0xf7) the value is a server-wide count of movement updates: 493 at 0.1 s,
282,287 at 168 s, 1,476,401 at 679 s of the replay -- not a time.

The header's own byte coding is not learnt yet (its first byte picks the coding of the rest), so our server takes the
replay's own headers, sorted by their value, as an increasing sequence: each 552 we send gets the next one, which is
what the client needs (every new path of a unit carries a value >= its last).

  sync552.py        builds research/exe133/s2c_552_sync_heads.json ([[value, head hex], ...] sorted)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'research', 'exe133', 's2c_552_sync_heads.json')
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


def next_head(at_least=0):
    """the next header of the sequence (bytes), its value >= at_least and > every one given before"""
    global _heads
    if _heads is None:
        _heads = json.load(open(OUT))
    i = _next[0]
    while i < len(_heads) - 1 and _heads[i][0] < at_least:
        i += 1
    _next[0] = min(i + 1, len(_heads) - 1)
    return bytes.fromhex(_heads[i][1]), _heads[i][0]


if __name__ == '__main__':
    build()
