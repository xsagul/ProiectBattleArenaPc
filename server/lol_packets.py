"""Game packets of the 13.3 protocol that the test server reads or writes, worked out by running the client's own code
in the emulator (server/c2s_emu.py, packet_emu.py). Write-up: docs/MIGRARE_12.23.md "Darius la click".

491  client -> server, an order (right click). Wire body after [u16 id][u32 net id = the hero]:
       u8  random (rand() & 0xff)
       u8  flags: low 3 bits = order type 0 / 1 / 2 as 2 / 5 / 7; 0 = a byte with the type follows; bit 0x10 clear =
           the field +0x14 follows (a varint, not handled here); bit 0x40 clear = 8 bytes of the field +0x18 follow
       varint length, then that many bytes: the path the client computed, in the waypoint-entry format of 552,
           written last byte first, every byte through F (c2s_491_bytemap.txt)
       then the field +0x30 (not read here)
     Order type 2 = move. Measured on three clicks: the path is [hero position, clicked point].

552  server -> client, the movement packet (WaypointGroup). Wire body:
       u8 b0, u8 b1, u8 b2 [, one more byte for some b0], varint length (through H), then H(buffer)
     buffer = waypoint entries (format in waypoints.py). Checked on 400 replay packets: body after the header is
     exactly H(buffer) and the varint is the buffer's length.
"""
import json
import os
import struct

import waypoints as W

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'exe133')
F = [int(x, 16) for x in open(os.path.join(RES, 'c2s_491_bytemap.txt')).read().split()]
FINV = {v: k for k, v in enumerate(F)}
H = json.load(open(os.path.join(RES, 's2c_552_bytemap.json')))
HINV = {v: k for k, v in enumerate(H)}
ORDER_IN_FLAGS = {2: 0, 5: 1, 7: 2}


def _varint(read):
    v, shift = 0, 0
    while True:
        b = read()
        v |= (b & 0x7f) << shift
        shift += 7
        if not b & 0x80:
            return v


def decode_491(body):
    """-> {'type': order type, 'path': [(x, z) map cells], 'net': mover, 'speed': ...} or None when not understood."""
    at = 2
    flags = body[1]
    order = ORDER_IN_FLAGS.get(flags & 7)
    if order is None:
        order = body[at]
        at += 1
    if not flags & 0x10:
        return {'type': order, 'path': None, 'why': 'field +0x14 present'}
    if not flags & 0x40:
        at += 8

    def rd():
        nonlocal at
        at += 1
        return FINV[body[at - 1]]
    n = _varint(rd)
    raw = bytes(FINV[b] for b in body[at:at + n])[::-1]
    try:
        ent = W.parse(raw)[0]
    except Exception as e:
        return {'type': order, 'path': None, 'why': f'path: {e}', 'raw': raw.hex()}
    return {'type': order, 'path': ent['points'], 'net': ent['net'], 'speed': ent['speed']}


def waypoint_entry(net, points, speed, flags=0xc0):
    """One entry with every coordinate as an i16 (no delta bytes)."""
    n = len(points)
    out = struct.pack('<BBIf', 2 * n, flags, net, speed)
    out += bytes((2 * (n - 1) + 7) // 8 if n > 1 else 0)
    for x, z in points:
        out += struct.pack('<hh', x, z)
    return out


def waypoint_teleport(net, point, speed, teleport_id, flags=0xe0):
    """One entry that puts a unit at a point at once (Flash): odd size = a teleport id byte follows the speed (the
    unit's own teleport counter, 2..17 in the replay), one point. Measured on the replay's 34 Flash teleports."""
    return struct.pack('<BBIfB', 3, flags, net, speed, teleport_id) + struct.pack('<hh', *point)


def _len_bytes(n):
    out = b''
    while True:
        b = n & 0x7f
        n >>= 7
        out += bytes([H[b | (0x80 if n else 0)]])
        if not n:
            return out


TEMPLATE_HEAD = bytes.fromhex('0e6045')   # b0 b1 b2 of a replay 552 with a 4-byte header (Darius at 15.15 s)


SYNC_FLOOR = 150000   # above the values the replay's start state / spawn packets give units (sync552.py)


def encode_552(buffer, head=None):
    """head None: the next value of our increasing movement sequence (sync552.py: the client rejects a unit's path
    whose header value is below the unit's last one)"""
    if head is None:
        import sync552
        head = sync552.next_head(SYNC_FLOOR)[0]
    return head + _len_bytes(len(buffer)) + bytes(H[b] for b in buffer)


def split_552(body):
    """-> (head bytes, buffer) of a 552 body, or None."""
    for hl in (4, 5, 6, 7):
        for lb in (1, 2):
            if hl - lb < 3:
                continue
            vals = [HINV[b] for b in body[hl - lb:hl]]
            if lb == 2 and not vals[0] & 0x80 or lb == 1 and vals[0] & 0x80:
                continue
            n = vals[0] & 0x7f if lb == 1 else (vals[0] & 0x7f) | (vals[1] << 7)
            if n == len(body) - hl:
                return body[:hl - lb], bytes(HINV[b] for b in body[hl:])
    return None


def without_unit(body, net):
    """The 552 body with every entry of one unit taken out; None when nothing is left; the body itself when the
    packet cannot be split."""
    s = split_552(body)
    if s is None:
        return body
    head, buf = s
    try:
        ent = W.parse(buf)
    except Exception:
        return body
    if not any(e['net'] == net for e in ent):
        return body
    keep, at = b'', 0
    for e in ent:   # re-split the buffer into the raw entries, in order
        size, n = buf[at], buf[at] >> 1
        ln = 10 + (size & 1) + ((2 * (n - 1) + 7) // 8 if n > 1 else 0)
        bits = int.from_bytes(buf[at + ln - ((2 * (n - 1) + 7) // 8 if n > 1 else 0):at + ln], 'little')
        ln += 4
        for k in range(2 * (n - 1)):
            ln += 1 if bits >> k & 1 else 2
        if e['net'] != net:
            keep += buf[at:at + ln]
        at += ln
    if not keep:
        return None
    return head + _len_bytes(len(keep)) + bytes(H[b] for b in keep)


# 676 = a spell's new level (the answer to 384), 606 = the hero's new level. Bodies taken from the replay, keyed by
# their fields in clear: 676 "slot,1,level,0", 606 "level,skill points added". data/exe133/s2c_676_606_bodies.json
BODIES = json.load(open(os.path.join(RES, 's2c_676_606_bodies.json')))


def skill_up_676(slot, level):
    b = BODIES.get(f'676:{slot},1,{level},0')
    return bytes.fromhex(b[0]) if b else None


def decode_384(body):
    """384 = the client asks to raise a spell (Ctrl+Q/W/E/R). Body for slots 0..3, from the client's own constructor
    (rva 0x535d30) and writer (rva 0x94b9e0) run in the emulator; slot 0 = e5 matches the capture."""
    return DECODE_384.get(body.hex())


DECODE_384 = {'e5': 0, 'e0': 1, 'e6': 2, 'e47f': 3}


# 595 = replication (replication.py has the buffer format). Wire body: u8 b0, u8 b1, varint length (through M), the
# buffer written last byte first through M (data/exe133/s2c_595_bytemap.json), then a trailer (sync counters).
# Measured by flipping each byte of a replay packet through the client's reader.
M = json.load(open(os.path.join(RES, 's2c_595_bytemap.json')))
MINV = {v: k for k, v in enumerate(M)}
TEMPLATE_595 = (bytes.fromhex('e98c'), bytes.fromhex('53325135f36b'))   # head and trailer of a replay packet


def _varint_through(table, n):
    out = b''
    while True:
        b = n & 0x7f
        n >>= 7
        out += bytes([table[b | (0x80 if n else 0)]])
        if not n:
            return out


def split_595(body):
    """-> (head, buffer, trailer) or None"""
    at, n, shift = 2, 0, 0
    while at < len(body):
        b = MINV[body[at]]
        at += 1
        n |= (b & 0x7f) << shift
        shift += 7
        if not b & 0x80:
            break
    if at + n > len(body):
        return None
    return body[:2], bytes(MINV[c] for c in body[at:at + n])[::-1], body[at + n:]


def join_595(head, buf, trailer):
    return head + _varint_through(M, len(buf)) + bytes(M[c] for c in buf[::-1]) + trailer


def packed_int(v):
    out = b''
    while True:
        b = v & 0x7f
        v >>= 7
        out += bytes([b | (0x80 if v else 0)])
        if not v:
            return out


def replication_unit(net, groups):
    """groups: {group: [(bit, raw value bytes)]} -> one unit of a replication buffer"""
    primary = 0
    out = b''
    for g in sorted(groups):
        primary |= 1 << g
        mask, data = 0, b''
        for bit, raw in sorted(groups[g]):
            mask |= 1 << bit
            data += raw
        out += struct.pack('<IB', mask, len(data)) + data
    return bytes([primary]) + struct.pack('<I', net) + out


def take_unit(body, net):
    """(the 595 body without that unit or None when nothing is left, the unit's groups {group: (mask, bytes)});
    (body, None) when the unit is not in it or the packet cannot be split"""
    import replication as RP
    sp = split_595(body)
    if sp is None:
        return body, None
    head, buf, trailer = sp
    try:
        units = RP.parse(buf)
    except Exception:
        return body, None
    mine = [g for n, g in units if n == net]
    if not mine:
        return body, None
    out = b''
    for n, g in units:
        if n == net:
            continue
        primary = sum(1 << k for k in g)
        out += bytes([primary]) + struct.pack('<I', n) + b''.join(struct.pack('<IB', m, len(d)) + d for k, (m, d) in sorted(g.items()))
    return (join_595(head, out, trailer) if out else None), mine[0]


def without_group(body, net, group):
    """The 595 body without one group of one unit (the unit goes when nothing is left); None when the packet is
    left empty; the body itself when it cannot be split."""
    import replication as RP
    s = split_595(body)
    if s is None:
        return body
    head, buf, trailer = s
    try:
        units = RP.parse(buf)
    except Exception:
        return body
    if not any(n == net and group in g for n, g in units):
        return body
    out = b''
    for n, g in units:
        if n == net:
            g = {k: v for k, v in g.items() if k != group}
            if not g:
                continue
        primary = sum(1 << k for k in g)
        out += bytes([primary]) + struct.pack('<I', n) + b''.join(struct.pack('<IB', m, len(d)) + d for k, (m, d) in sorted(g.items()))
    if not out:
        return None
    return join_595(head, out, trailer)
