"""The 13.3 replication packet (id 595): every unit's replicated numbers (health, mana, stats...) as they change.

Object: +0x0c the buffer, +0x10 its length, +0x18 u8 the number of units, +0x1c / +0x20 sync counters. The buffer,
unit after unit [measured: every buffer of the replay parses to its last byte]:
    u8  primary mask: one bit per group of values (6 groups)
    u32 net id
    for each set bit, low to high:
        u32 secondary mask: one bit per value of the group
        u8  the size of the values that follow
        the values, low bit first: floats and packed ints (see take())
The same value is sent once per viewer, so a spectator replay holds each update several times with only the
counter changed: seen() drops the repeats.

  replication.py fields <netid hex> [seconds from] [to]   every (group, bit) of a unit: how often, first / last value
  replication.py track <netid hex> <group> <bit>          one value over time
  replication.py check                                     parse every buffer of the replay
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decoded


def parse(buf):
    """[(net id, {group: (secondary mask, the group's bytes)})]; raises when the buffer does not parse to its end"""
    out, at = [], 0
    while at < len(buf):
        primary = buf[at]
        net = struct.unpack_from('<I', buf, at + 1)[0]
        at += 5
        groups = {}
        for g in range(8):
            if not primary >> g & 1:
                continue
            mask, size = struct.unpack_from('<IB', buf, at)
            at += 5
            if at + size > len(buf):
                raise ValueError('short group')
            groups[g] = (mask, buf[at:at + size])
            at += size
        out.append((net, groups))
    if at != len(buf):
        raise ValueError(f'{len(buf) - at} bytes left')
    return out


def take(data, at, kind):
    """one value at data[at:]: its end. A float is 4 bytes, or 0xff alone (zero), or 0xfe then its 4 bytes (a float
    whose own first byte is 0xfe / 0xff). An int is packed: 7 bits a byte, low first, the high bit = more follow."""
    if kind == 'f':
        if data[at] == 0xff:
            return at + 1
        return at + (5 if data[at] == 0xfe else 4)
    while data[at] & 0x80:
        at += 1
    return at + 1


def as_float(raw):
    if raw == b'\xff':
        return 0.0
    if len(raw) == 5 and raw[0] == 0xfe:
        return struct.unpack('<f', raw[1:])[0]
    if len(raw) == 4:
        return struct.unpack('<f', raw)[0]
    return None


def as_int(raw):
    v = 0
    for k, c in enumerate(raw):
        v |= (c & 0x7f) << (7 * k)
    return v


def raw_updates():
    """(seconds, net id, {group: (mask, bytes)}) in stream order, the per-viewer repeats dropped"""
    last = None
    for r in decoded.packets({595}):
        f = decoded.fields(r)
        size = struct.unpack('<I', f.get(0x10, b'\0\0\0\0'))[0]
        buf = decoded.blob(r, 1, size)
        if last == (r['t'], buf):
            continue
        last = (r['t'], buf)
        try:
            units = parse(buf)
        except (ValueError, struct.error, IndexError):
            raw_updates.bad += 1
            continue
        raw_updates.ok += 1
        for net, groups in units:
            yield r['t'], net, groups


raw_updates.ok = raw_updates.bad = 0


def updates():
    """(seconds, net id, {(group, bit): raw value}) with each group's bytes cut into its values.

    Which bits are floats and which packed ints is not in the packet: it is learnt per unit from the groups that
    carry one value (4 bytes, 0xff or 0xfe + 4 = a float; anything else = an int), then used on the groups that
    carry several. A group with a bit of unknown kind after its first value yields only the values before it."""
    every = list(raw_updates())
    kind = {}
    for t, net, groups in every:
        for g, (mask, data) in groups.items():
            if mask & (mask - 1) == 0 and mask and data:
                b = mask.bit_length() - 1
                isf = len(data) == 4 or data == b'\xff' or (len(data) == 5 and data[0] == 0xfe)
                if kind.get((net, g, b), 'f') == 'f':
                    kind[(net, g, b)] = 'f' if isf else 'i'
    for t, net, groups in every:
        vals = {}
        for g, (mask, data) in groups.items():
            bits = [b for b in range(32) if mask >> b & 1]
            if len(data) == 4 * len(bits) and not any(kind.get((net, g, b)) == 'i' for b in bits):
                for k, b in enumerate(bits):
                    vals[(g, b)] = data[4 * k:4 * k + 4]
                continue
            at = 0
            for b in bits:
                k = kind.get((net, g, b))
                if k is None or at >= len(data):
                    break
                end = take(data, at, k)
                vals[(g, b)] = data[at:end]
                at = end
        yield t, net, vals


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fields':
        want = int(sys.argv[2], 16)
        t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0
        t1 = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
        seen = collections.OrderedDict()
        for t, net, vals in updates():
            if net != want or not t0 <= t <= t1:
                continue
            for k, raw in vals.items():
                e = seen.setdefault(k, [0, t, raw, t, raw])
                e[0] += 1
                e[3], e[4] = t, raw
        show = lambda raw: f'{as_float(raw):.3f}' if as_float(raw) is not None and len(raw) == 4 else raw.hex()
        for (g, b), (n, ta, ra, tb, rb) in sorted(seen.items()):
            print(f'group {g} bit {b:2}  x{n:5}  first {ta:8.2f} s {show(ra):>14} ({ra.hex()})   last {tb:8.2f} s {show(rb):>14} ({rb.hex()})')
        print(f'buffers parsed {raw_updates.ok}, not parsed {raw_updates.bad}', file=sys.stderr)
    elif cmd == 'track':
        want, g, b = int(sys.argv[2], 16), int(sys.argv[3]), int(sys.argv[4])
        for t, net, vals in updates():
            if net == want and (g, b) in vals:
                raw = vals[(g, b)]
                print(f'{t:9.3f}  {as_float(raw)}  {raw.hex()}')
    elif cmd == 'check':
        for _ in raw_updates():
            pass
        print(f'buffers parsed {raw_updates.ok}, not parsed {raw_updates.bad}')
