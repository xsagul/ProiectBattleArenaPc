"""The client's requests read into values (formats learnt from the client's own writers by c2s16.py and kept in
data/exe1620/codec/c2s_<id>.json; this is the plain reader: no emulator at run time).

    order(body)   1032 -> {'place': (x, z), 'target': net id, 'kind': byte}        kind 0x91 move, 0xed attack [m]
    skill(body)   544  -> slot 0..3 or None
    cast(body)    707  -> {'hash', 'target', 'target_place', 'slot', 'caster_place', 'flags', 'cursor'}
    buy(body)     1135 -> item id
    ping(body)    841  -> (number bytes, client time bytes)
"""
import functools
import json
import os
import struct

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'exe1620', 'codec')
ORDER, SKILL_UP, CAST, BUY, PING, LOADING, READY, HELLO = 1032, 544, 707, 1135, 841, 197, 64, 1
SELL, UNDO, RECALL_REQUEST, SWAP = 745, 1249, 167, 1151
HEARTBEAT, HEARTBEAT_ANSWER = 1084, 665


def heartbeat_answer(body):
    """[m: all 426 pairs of the live recording] every 10 s the client sends 1084 on channels 2 and 1 with a counter
    (1, 2, 3, ...); the server answers 665 on the same channel with the channel's number and that counter. Both
    packets carry the counter in the same bytes; only the header byte's top two bits differ."""
    return bytes([body[0] ^ 0xc0]) + body[1:] if body else None



def nid_number(v):
    return v if v & 0xffffff == 0 else v ^ 0x40000000


@functools.lru_cache(maxsize=None)
def load(name):
    spec = json.load(open(os.path.join(RES, f'c2s_{name}.json')))
    for f in spec.get('fields', []):
        f['modes'] = {int(m): d for m, d in f['modes'].items()}
        for d in f['modes'].values():
            if d['kind'] == 'fixed':
                d['inv'] = [{w: b for b, w in enumerate(tab) if w is not None} for where, tab in d['map']]
    spec['by_off'] = {f['off']: f for f in spec.get('fields', [])}
    return spec


def decode(spec, body):
    """a packet's bytes after the id and the net id -> {field offset: value bytes} (+ 'rest'), or None"""
    try:
        H = spec['header']
        h = int.from_bytes(body[:H], 'little')
        at = H
        out = {}
        for off in spec['order']:
            f = spec['by_off'][off]
            d = f['modes'].get((h >> f['bit']) & ((1 << f['width']) - 1))
            if d is None:
                return None
            if d['kind'] == 'const':
                out[off] = bytes.fromhex(d['value'])
            elif d['kind'] == 'fixed':
                v = bytearray(f['size'])
                for j, (where, tab) in enumerate(d['map']):
                    v[j] = d['inv'][j][body[at + where]]
                out[off] = bytes(v)
                at += d['n']
            else:
                x, shift = 0, 0
                while True:
                    g = d['S'][body[at]]
                    at += 1
                    x |= (g & 0x7f) << shift
                    shift += 7
                    if not g & 0x80:
                        break
                x &= (1 << (8 * f['size'])) - 1
                out[off] = (nid_number(x) if d.get('nid') else x).to_bytes(f['size'], 'little')
        out['rest'] = body[at:]
        return out
    except (IndexError, KeyError, TypeError):
        return None


def order(body):
    v = decode(load(ORDER), body)
    if v is None:
        return None
    return {'place': struct.unpack('<ff', v[0x18]), 'target': struct.unpack('<I', v[0x20])[0], 'kind': v[0x24][0]}


def skill(body):
    """544: one header byte whose low 3 bits say the slot (constant modes), else a byte follows [m]"""
    s = json.load(open(os.path.join(RES, 'c2s_544_slot.json'))) if not hasattr(skill, 'spec') else skill.spec
    skill.spec = s
    if not body:
        return None
    mode = body[0] & 7
    slot = s['const_modes'].get(str(mode))
    if slot is None and mode == s['fixed_mode'] and len(body) > 1:
        slot = s['fixed'].get(str(body[1]))
    return slot


def cast(body):
    v = decode(load('707.10'), body[1:])
    if v is None:
        return None
    xz = lambda b: struct.unpack('<ff', b)
    return {'hash': struct.unpack('<I', v[0x8])[0], 'target': struct.unpack('<I', v[0xc])[0], 'target_place': xz(v[0x10]),
            'slot': v[0x18][0], 'caster_place': xz(v[0x1c]), 'flags': v[0x24][0], 'cursor': xz(v[0x28])}


def buy(body):
    v = decode(load(BUY), body)
    return None if v is None else int.from_bytes(v[0x14], 'little')


def ping(body):
    v = decode(load(PING), body)
    return None if v is None else (v[0x10], v[0x18])


def generic(pid, body):
    """any learnt request -> {offset: bytes} or None"""
    try:
        return decode(load(pid), body)
    except FileNotFoundError:
        return None
