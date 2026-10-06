"""The 13.3 movement packet (id 552, WaypointGroup), its buffer read in clear by packet_emu.py.

Object: +0x0a u16 entries, +0x0c u32 a sync counter, +0x10 the buffer (+0x14 its length). The buffer, entry after
entry [measured: every buffer of the replay parses to its last byte]:
    u8  2 x the number of points, + 1 when a teleport id follows
    u8  flags
    u32 net id
    f32 speed
    [u8 teleport id]
    ceil(2 (n - 1) / 8) bytes: one bit per coordinate after the first point, 1 = a signed byte added to the previous
        value, 0 = an i16 of its own
    i16 x0, i16 z0, then the other coordinates
Coordinates are map cells relative to the map's middle; to_world() turns them into world units.
"""
import struct


def parse(buf):
    out, at = [], 0
    while at < len(buf):
        size, flags = buf[at], buf[at + 1]
        net, speed = struct.unpack_from('<If', buf, at + 2)
        at += 10
        n = size >> 1
        teleport = None
        if size & 1:
            teleport = buf[at]
            at += 1
        nflag = (2 * (n - 1) + 7) // 8 if n > 1 else 0
        bits = int.from_bytes(buf[at:at + nflag], 'little')
        at += nflag
        x, z = struct.unpack_from('<hh', buf, at)
        at += 4
        pts = [(x, z)]
        for k in range(1, n):
            c = []
            for j, prev in enumerate((x, z)):
                b = 2 * (k - 1) + j
                if bits >> b & 1:
                    v = prev + struct.unpack_from('<b', buf, at)[0]
                    at += 1
                else:
                    v = struct.unpack_from('<h', buf, at)[0]
                    at += 2
                c.append(v)
            x, z = c
            pts.append((x, z))
        out.append({'net': net, 'flags': flags, 'speed': speed, 'teleport': teleport, 'points': pts})
    if at != len(buf):
        raise ValueError(f'{len(buf) - at} bytes left')
    return out


# [măsurat: 1517 attack positions of packets 592 / 286 / 26 against the mover's latest first point] a step is 2 world
# units and (0, 0) is the middle of the navigation grid's bounds, (min + max) / 2 of AIPath_SRX_2.aimesh_ngrid
CELL = 2.0
CENTER = (7358.6477, 7412.4834)


def to_world(p):
    return (p[0] * CELL + CENTER[0], p[1] * CELL + CENTER[1])
