"""Replication on 16.20 (packet 287): a unit's replicated numbers written by name.

The packet (format learnt by pkt_schema, data/exe1620/codec/287.tree.json): +0x10 u8 units in the buffer,
+0x14 u32 a counter that only grows, +0x18 f32 game time, +0x20 the buffer. The buffer is 13.3's (replication.py):
per unit u8 group mask, u32 net id, then per group u32 value mask, u8 size, the values low bit first; a value is a
float (4 bytes; 0 = 0xff alone; 0xfe in front when its first byte is 0xfe / 0xff) or a packed int.
[measured: 300 of 300 buffers of the 16.20 replay parse to their last byte with replication.parse]

Names: every unit class has its group tables in the client's data, 0x2a0 bytes each, in group order:
u32 count, u32 float mask (bit i = value i is a float), u32 offsets[32], names[32] (pointer, length, capacity),
the owner class's name, 8 more bytes. They are filled at run time, so they are read from the image of a client
in a match (exe_image_live.bin).

  repl16.py names        -> data/exe1620/repl_names.json; prints every class's groups
  repl16.py check [n]    hero units of n replay packets: values read by name, written again, same bytes
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['BA_PATCH'] = '1620'
RES = os.path.join(HERE, '..', 'data', 'exe1620')
REPL = 287
HERO = 'AIHero'
# a lane minion uses 8 of the class's 10 tables (13.3 had the same split by a flag of the unit); with these, group 3
# is the health group, as the replay's minion updates need
MINION_TABLES = [0, 1, 2, 4, 6, 7, 8, 9]


def make_names():
    import packet_emu16 as P
    img = P.IMG
    size, at = P._SECS['.data']

    def text(o):
        a, n, c = struct.unpack_from('<QII', img, o)
        r = a - P.BASE
        if a and 0 < r < len(img) and 0 < n < 80:
            s = img[r:r + n]
            if img[r + n] == 0 and all(32 <= ch < 127 for ch in s):
                return s.decode()
        return None
    tables = {}
    for o in range(at + 0x288, at + size - 0x18, 8):
        owner = text(o)
        if not owner or not re.match(r'^[A-Z][A-Za-z_]+$', owner):
            continue
        count, mask = struct.unpack_from('<II', img, o - 0x288)
        if count > 32:
            continue
        names = [text(o - 0x200 + 16 * i) for i in range(32)]
        if any(x is None for x in names[:count]) or any(x is not None for x in names[count:]):
            continue
        offs = struct.unpack_from('<32I', img, o - 0x280)
        if any(offs[count:]):
            continue
        tables.setdefault(owner, []).append({'at': o - 0x288, 'flags': mask,
                                             'values': [{'bit': i, 'name': names[i], 'offset': offs[i]} for i in range(count)]})
    out = {}
    for owner, ts in tables.items():
        ts.sort(key=lambda t: t['at'])
        # a class's tables lie 0x2a0 apart; keep the longest such run that holds values
        runs, run = [], [ts[0]]
        for t in ts[1:]:
            if t['at'] - run[-1]['at'] == 0x2a0:
                run.append(t)
            else:
                runs.append(run)
                run = [t]
        runs.append(run)
        best = max(runs, key=lambda r: (sum(len(t['values']) for t in r), len(r)))
        if sum(len(t['values']) for t in best) == 0 or len(best) < 6:
            continue
        out[owner] = {'groups': [hex(t['at']) for t in best], 'flags': [t['flags'] for t in best],
                      'values': {str(g): t['values'] for g, t in enumerate(best)}}
    if 'AIMinionCommon' in out and len(out['AIMinionCommon']['groups']) == 10:
        m = out['AIMinionCommon']
        out['lane_minion'] = {'groups': [m['groups'][i] for i in MINION_TABLES], 'flags': [m['flags'][i] for i in MINION_TABLES],
                              'values': {str(g): m['values'][str(i)] for g, i in enumerate(MINION_TABLES)}}
    json.dump(out, open(os.path.join(RES, 'repl_names.json'), 'w'), indent=0)
    return out


_cls = None


def names(cls=HERO):
    """{name: (group, bit, 'f' | 'i')}"""
    global _cls
    if _cls is None:
        d = json.load(open(os.path.join(RES, 'repl_names.json')))
        _cls = {}
        for key, c in d.items():
            _cls[key] = {v['name']: (int(g), v['bit'], 'f' if c['flags'][int(g)] >> v['bit'] & 1 else 'i')
                         for g, vals in c['values'].items() for v in vals}
    return _cls[cls]


def enc_value(kind, v):
    if kind == 'f':
        if v == 0:
            return b'\xff'
        raw = struct.pack('<f', v)
        return (b'\xfe' + raw) if raw[0] in (0xfe, 0xff) else raw
    v = int(v) & 0xffffffffffffffff
    out = bytearray()
    while True:
        b = v & 0x7f
        v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


def dec_values(kinds, data):
    """the values of one group: kinds = 'f' / 'i' per set bit, in order -> list of numbers (raises when it does not fit)"""
    out, at = [], 0
    for k in kinds:
        if k == 'f':
            if data[at] == 0xff:
                out.append(0.0)
                at += 1
            else:
                if data[at] == 0xfe:
                    at += 1
                out.append(struct.unpack_from('<f', data, at)[0])
                at += 4
        else:
            v = shift = 0
            while True:
                b = data[at]
                at += 1
                v |= (b & 0x7f) << shift
                shift += 7
                if not b & 0x80:
                    break
            out.append(v)
    if at != len(data):
        raise ValueError(f'{len(data) - at} bytes left')
    return out


def unit(net, values, cls=HERO):
    """one unit of a replication buffer: values {name: number}"""
    table = names(cls)
    groups = {}
    for name, v in values.items():
        g, b, kind = table[name]
        groups.setdefault(g, {})[b] = enc_value(kind, v)
    primary, out = 0, b''
    for g in sorted(groups):
        primary |= 1 << g
        mask = sum(1 << b for b in groups[g])
        data = b''.join(groups[g][b] for b in sorted(groups[g]))
        out += struct.pack('<IB', mask, len(data)) + data
    return bytes([primary]) + struct.pack('<I', net) + out


def read_unit(groups, cls=HERO):
    """{group: (mask, bytes)} as replication.parse gives it -> {name: number}"""
    by = {(g, b): (n, k) for n, (g, b, k) in names(cls).items()}
    out = {}
    for g, (mask, data) in groups.items():
        bits = [b for b in range(32) if mask >> b & 1]
        vals = dec_values([by[(g, b)][1] for b in bits], data)
        for b, v in zip(bits, vals):
            out[by[(g, b)][0]] = v
    return out


_sc = None


def packet(units, game_time=0.0, counter=0):
    """units: [(net id, {name: number}, class)] -> body of packet 287 (its net id is 0)"""
    global _sc
    import pkt_schema as S
    if _sc is None:
        _sc = S.Schema.load(REPL)
    buf = b''.join(unit(n, v, c) for n, v, c in units)
    return _sc.encode({'+0x10': f'{len(units):02x}', '+0x14': struct.pack('<I', counter).hex(),
                       '+0x18': struct.pack('<f', game_time).hex(), '+0x20': {'text': buf.hex()}})


if __name__ == '__main__':
    if sys.argv[1] == 'names':
        d = make_names()
        for owner, c in d.items():
            print(owner, 'groups:', {g: len(v) for g, v in c['values'].items() if v})
        for g, vals in d[HERO]['values'].items():
            print(f'  hero group {g}:', ', '.join(v['name'] for v in vals[:9]) + (' ...' if len(vals) > 9 else ''))
    elif sys.argv[1] == 'check':
        import types
        sys.modules['decoded'] = types.ModuleType('decoded')
        import replication
        import x_buf
        import packet_emu16 as P
        import rofl2
        r = rofl2.Rofl2(P.ROFL)
        heroes = {obj for e, (t, ch, pid, obj, body) in rofl2.stream(r, (2,)) if pid in (905, 227) and e['id'] == 1}
        same = diff = bad = 0
        seen = {}
        for tm, head, buf in x_buf.buffers(REPL, 0x20, int(sys.argv[2]) if len(sys.argv) > 2 else 300, kinds=((1,),)):
            at = 0
            for net, groups in replication.parse(buf):
                if net not in heroes:
                    continue
                try:
                    v = read_unit(groups)
                except Exception as x:
                    bad += 1
                    if bad <= 3:
                        print(f'  hero {net:#x} at {tm:.2f}: {type(x).__name__} {x}')
                    continue
                raw = bytes([sum(1 << g for g in groups)]) + struct.pack('<I', net) + b''.join(
                    struct.pack('<IB', m, len(d)) + d for g, (m, d) in sorted(groups.items()))
                if unit(net, v) == raw:
                    same += 1
                else:
                    diff += 1
                for k, x in v.items():
                    seen.setdefault(k, x)
        print(f'hero units: {same} written again with the same bytes, {diff} differ, {bad} not readable by name')
        print('first values seen:', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in list(seen.items())[:24]})
