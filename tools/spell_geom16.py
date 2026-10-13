"""The geometry of every champion spell as the real server played it, measured over the sampled casts of the replays
and written into the spell's template (data/exe1620/spells16/<Champion>.json, key 'geom'):

    reach     |end - launch| of the cast struct (1215 +0xac, +0x124): {'med', 'lo', 'hi'} - a spell whose reach is the
              same in every cast is a line of that length, one whose reach varies ends where it was aimed
    targeted  share of the casts that named a unit (+0x8)
    missiles  {missile spell hash: {'n' per cast, 'dt', 'speed' (+0x98), 'accel' (+0xf0), 'min' (+0x40), 'max'
              (+0x234), 'len' {'med', 'lo', 'hi'} (|+0x54 - +0x14|), 'angles' [degrees from the cast's direction, one
              per missile of a fan], 'from_caster' share starting at the launch place, 'homing' share with a target
              unit, 'to_caster' share whose target is the caster}}
    dash      the caster's 1140: {'share', 'dt', 'speed', 'len' {'med', 'lo', 'hi'}, 'angle' (degrees from the cast's
              direction)}

    python tools/spell_geom16.py [Champion ..]
"""
import collections
import glob
import json
import math
import os
import pickle
import statistics
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import spell_templates16 as ST
BY_CHAMP = os.path.join(ROOT, 'data', 'replays16', 'by_champ')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'spells16')
CELL = 2.0


def vec3(h):
    try:
        return struct.unpack('<fff', bytes.fromhex(h)) if isinstance(h, str) and len(h) == 24 else None
    except Exception:
        return None


def f32(h):
    try:
        return struct.unpack('<f', bytes.fromhex(h))[0] if isinstance(h, str) and len(h) == 8 else None
    except Exception:
        return None


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and len(h) == 8 else None


def stats(xs):
    xs = sorted(xs)
    n = len(xs)
    return {'med': round(statistics.median(xs), 1), 'lo': round(xs[int(0.1 * (n - 1))], 1), 'hi': round(xs[int(round(0.9 * (n - 1)))], 1), 'n': n}


def angle(a, b):
    """signed degrees from direction a to direction b (x, z)"""
    return math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))


def circ_mean(deg):
    return math.degrees(math.atan2(sum(math.sin(math.radians(a)) for a in deg), sum(math.cos(math.radians(a)) for a in deg)))


def circ_spread(deg):
    """how far the angles lie from their mean direction (degrees, median)"""
    m = circ_mean(deg)
    return statistics.median(abs((a - m + 180.0) % 360.0 - 180.0) for a in deg)


def dash_entries(blob):
    """a 1140's movement group -> [{'net', 'speed', 'vec' (dx, dz world units from the first to the last point)}]"""
    out, at = [], 0
    while at + 66 <= len(blob):
        n = blob[at] >> 1
        net, _, speed, _ = struct.unpack_from('<Ifff', blob, at + 2)
        p = at + 66
        nflag = (2 * (n - 1) + 7) // 8 if n > 1 else 0
        bits = int.from_bytes(blob[p:p + nflag], 'little')
        p += nflag
        if p + 4 > len(blob):
            return out
        x, z = struct.unpack_from('<hh', blob, p)
        p += 4
        x0, z0 = x, z
        for k in range(1, n):
            c = []
            for j, prev in enumerate((x, z)):
                if bits >> (2 * (k - 1) + j) & 1:
                    if p + 1 > len(blob):
                        return out
                    c.append(prev + struct.unpack_from('<b', blob, p)[0])
                    p += 1
                else:
                    if p + 2 > len(blob):
                        return out
                    c.append(struct.unpack_from('<h', blob, p)[0])
                    p += 2
            x, z = c
        out.append({'net': net, 'speed': speed, 'vec': ((x - x0) * CELL, (z - z0) * CELL)})
        at = p
    return out


def spell_geom(samples):
    reach, targeted = [], 0
    mis = collections.defaultdict(lambda: collections.defaultdict(list))
    dash = collections.defaultdict(list)
    n = 0
    for s in samples:
        c = ((s.get('cast') or {}).get('+0x18')) or {}
        la, en = vec3(c.get('+0x124')), vec3(c.get('+0xac'))
        if la is None or en is None:
            continue
        n += 1
        d = (en[0] - la[0], en[2] - la[2])
        r = math.hypot(*d)
        reach.append(r)
        tl = c.get('+0x8') or []
        targeted += bool(tl)
        per = collections.defaultdict(list)
        dashed = False
        moved = 0.0                                                         # how far a dash of the cast took the caster
        evs = sorted(ST.own_events(s), key=lambda e: (e[0], 0 if e[1] == 1140 else 1))
        for dt, pid, role, net, ch, cont, v, raw in evs:                   # until the champion's next cast of its own
            if not isinstance(v, dict):
                continue
            if pid == 223 and role == 'missile':
                cs = v.get('+0xf8') or {}
                a, b = vec3(v.get('+0x14')), vec3(v.get('+0x54'))
                if a is None or b is None:
                    continue
                md = (b[0] - a[0], b[2] - a[2])
                tg = [u32(x.get('+0x8')) for x in (cs.get('+0x8') or []) if isinstance(x, dict)]
                per[cs.get('+0x18')].append({
                    'dt': dt, 'len': math.hypot(*md), 'ang': angle(d, md) if r > 1 and math.hypot(*md) > 1 else 0.0,
                    'speed': f32(v.get('+0x98')), 'accel': f32(v.get('+0xf0')), 'min': f32(v.get('+0x40')), 'max': f32(v.get('+0x234')),
                    'from': math.hypot(a[0] - la[0], a[2] - la[2]) < 60.0 + moved + 450.0 * max(0.0, dt - 0.3),
                    'homing': bool(tg), 'to_caster': s['net'] in tg,
                    'slot': cs.get('+0x60')})
            elif pid == 1140 and role == 'caster' and not dashed and dt <= 3.0:
                try:
                    es = [e for e in dash_entries(bytes.fromhex(v['+0x18']['text'])) if e['net'] == s['net']]
                except Exception:
                    es = []
                if es:
                    dashed = True
                    L = math.hypot(*es[0]['vec'])
                    moved = L + 40.0
                    dash['dt'].append(dt)
                    dash['speed'].append(es[0]['speed'])
                    dash['len'].append(L)
                    dash['ang'].append(angle(d, es[0]['vec']) if r > 1 and L > 1 else 0.0)
        for h, lst in per.items():
            first = min(x['dt'] for x in lst)
            wave = [x for x in lst if x['dt'] <= first + 0.02]            # the missiles of the first frame: a fan
            mis[h]['n'].append(len(wave))
            mis[h]['total'].append(len(lst))
            mis[h]['dt'].append(first)
            mis[h]['angles'].append(sorted(x['ang'] for x in wave))
            for k in ('len', 'speed', 'accel', 'min', 'max'):
                mis[h][k] += [x[k] for x in wave if x[k] is not None]
            mis[h]['from'] += [x['from'] for x in wave]
            mis[h]['homing'] += [x['homing'] for x in wave]
            mis[h]['to_caster'] += [x['to_caster'] for x in wave]
            mis[h]['slot'].append(lst[0]['slot'])
    if not n:
        return None
    g = {'n': n, 'reach': stats(reach), 'targeted': round(targeted / n, 3), 'missiles': {}, 'dash': None}
    for h, m in mis.items():
        if not h or len(m['n']) < max(2, 0.25 * n):
            continue
        cnt = int(statistics.median(m['n']))
        fans = [a for a in m['angles'] if len(a) == cnt]
        ang = [round(statistics.median(f[i] for f in fans), 1) for i in range(cnt)] if fans else [0.0] * cnt

        def med(k):
            return round(statistics.median(m[k]), 2) if m[k] else None
        g['missiles'][h] = {'share': round(len(m['n']) / n, 3), 'n': cnt, 'total': int(statistics.median(m['total'])),
                            'dt': round(statistics.median(m['dt']), 3), 'speed': med('speed'), 'accel': med('accel'),
                            'min': med('min'), 'max': med('max'), 'len': stats(m['len']) if m['len'] else None, 'angles': ang,
                            'from_caster': round(sum(m['from']) / max(1, len(m['from'])), 3),
                            'homing': round(sum(m['homing']) / max(1, len(m['homing'])), 3),
                            'to_caster': round(sum(m['to_caster']) / max(1, len(m['to_caster'])), 3),
                            'slot': collections.Counter(m['slot']).most_common(1)[0][0]}
    if len(dash['dt']) >= max(2, 0.4 * n):
        g['dash'] = {'share': round(len(dash['dt']) / n, 3), 'dt': round(statistics.median(dash['dt']), 3),
                     'speed': round(statistics.median(dash['speed']), 1), 'len': stats(dash['len']),
                     'angle': round(circ_mean(dash['ang']), 1), 'angle_spread': round(circ_spread(dash['ang']), 1)}
    return g


def build(champ):
    p = os.path.join(OUT, f'{champ}.json')
    sp = os.path.join(BY_CHAMP, f'{champ}.pkl')
    if not os.path.exists(p) or not os.path.exists(sp):
        return 0
    smp = collections.defaultdict(list)
    with open(sp, 'rb') as f:
        while True:
            try:
                part = pickle.load(f)
            except EOFError:
                break
            for k, lst in part.items():
                smp[k[1]] += lst
    d = json.load(open(p))
    k = 0
    for spell, t in d.items():
        g = spell_geom(smp.get(spell, []))
        t['geom'] = g
        k += g is not None
    json.dump(d, open(p, 'w'), indent=0)
    return k


if __name__ == '__main__':
    champs = sys.argv[1:] or sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(BY_CHAMP, '*.pkl')))
    for c in champs:
        try:
            print(c, build(c), 'spells with geometry', flush=True)
        except Exception as e:
            print(c, 'failed:', repr(e), flush=True)
