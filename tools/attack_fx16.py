"""The effects a champion's basic attacks make on Riot's server, from the replays (the cast evidence never looked at
attacks): for every champion attack (906) the packet-10 effects the champion makes before its next attack or cast.

    python tools/attack_fx16.py [n replays]      -> data/exe1620/attack_fx16.json

{champion: {'attacks': n, 'fx': {key hex: {'seen': attacks with it, 'delay': median s after the 906, 'bound':
 'caster' | 'target' | 'place', 'target': the instance names the attack's target, 'lasts': median s to its 584 (None:
 most end by themselves), 'ended': share ended by a 584, 'bone', 'target_bone', 'flags', 'tag', 'scale', 'keyword',
 'bins': {distance bin (100 units): [attacks, with this key]}}}}}
Read with the replays' own 10 format (data/exe1620/codec_fx, replaydb16). A key is played by the server when, among
the attacks at that distance, at least half had it (server/core/effects.py).
"""
import bisect
import collections
import json
import math
import multiprocessing as mp
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'attack_fx16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
WINDOW = 0.9


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def vec(h):
    try:
        return struct.unpack('<fff', bytes.fromhex(h)) if isinstance(h, str) and len(h) == 24 else None
    except Exception:
        return None


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
        H = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    except Exception as x:
        return gid, {}, repr(x)
    attacks = collections.defaultdict(list)      # hero -> [(t, target, dist)]
    casts = collections.defaultdict(list)
    fx = collections.defaultdict(list)           # caster -> [(t, key, inst, group)]
    ended = {}
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(906, 1215, 10, 584)):
        if t > 1200:
            break
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if v is None:
            continue
        if pid == 906 and net in H:
            a = v.get('+0x10') or {}
            there = vec(a.get('+0x10'))
            me = v.get('+0x48')
            d = None
            if there and isinstance(me, str) and len(me) == 16:
                x, z = struct.unpack('<ff', bytes.fromhex(me))
                d = math.hypot(there[0] - x, there[2] - z)
            attacks[net].append((t, u32(a.get('+0x20')), d))
        elif pid == 1215 and net in H:
            casts[net].append(t)
        elif pid == 10:
            for g in v.get('+0x10') or []:
                if not isinstance(g, dict):
                    continue
                for i in g.get('+0x10') or []:
                    if isinstance(i, dict) and u32(i.get('+0x18')) in H:
                        # [m] key 0: the effect is named by the ELF hash of an old particle path (+0x8) instead
                        key = g.get('+0x20') if g.get('+0x20') not in (None, '00000000') else 'old:' + str(g.get('+0x8'))
                        fx[u32(i.get('+0x18'))].append((t, key, i, g))
        elif pid == 584:
            ended.setdefault(u32(v.get('+0x14')), t)
    out = {}
    for hero, atks in attacks.items():
        champ = H[hero]
        c = out.setdefault(champ, {'attacks': 0, 'fx': {}})
        ats = [a[0] for a in atks]
        cts = casts.get(hero, [])
        per_attack = collections.defaultdict(set)
        rec = collections.defaultdict(list)
        for t, key, inst, g in fx.get(hero, []):
            i = bisect.bisect_right(ats, t) - 1
            if i < 0 or t - ats[i] > WINDOW:
                continue
            j = bisect.bisect_right(cts, t) - 1
            if j >= 0 and cts[j] >= ats[i] - 0.05:
                continue                          # a cast came between: the cast's effect
            ta, tgt, d = atks[i]
            per_attack[i].add(key)
            bound = u32(inst.get('+0x34'))
            eid = u32(inst.get('+0x38'))
            end = ended.get(eid)
            rec[key].append({'delay': t - ta, 'bound': 'caster' if bound == hero else 'target' if bound and bound == tgt else
                             'place' if not bound else 'other', 'target': u32(inst.get('+0xb8')) == tgt and tgt != 0,
                             'lasts': (end - t) if end is not None else None, 'bone': g.get('+0xc'),
                             'target_bone': g.get('+0x38'), 'flags': g.get('+0x50'), 'tag': (g.get('+0x28') or [None])[0],
                             'scale': inst.get('+0x14'), 'keyword': u32(inst.get('+0x3c')) == hero})
        for i, (ta, tgt, d) in enumerate(atks):
            b = str(int(d // 100)) if d is not None else '?'
            c['attacks'] += 1
            c.setdefault('bins', collections.Counter())[b] += 1
            for key in per_attack.get(i, ()):
                k = c['fx'].setdefault(key, {'seen': 0, 'bins': collections.Counter(), 'rec': []})
                k['seen'] += 1
                k['bins'][b] += 1
        for key, rs in rec.items():
            if key in c['fx']:
                c['fx'][key]['rec'].extend(rs[:400])
    return gid, out, ''


def most(xs):
    xs = [x for x in xs if x is not None]
    return collections.Counter(xs).most_common(1)[0][0] if xs else None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for champ, c in part.items():
                t = tot.setdefault(champ, {'attacks': 0, 'bins': collections.Counter(), 'fx': {}})
                t['attacks'] += c['attacks']
                t['bins'].update(c.get('bins', {}))
                for key, k in c['fx'].items():
                    tk = t['fx'].setdefault(key, {'seen': 0, 'bins': collections.Counter(), 'rec': []})
                    tk['seen'] += k['seen']
                    tk['bins'].update(k['bins'])
                    tk['rec'].extend(k['rec'])
            print(gid, len(part), err, flush=True)
    res = {}
    for champ, t in sorted(tot.items()):
        fxs = {}
        for key, k in t['fx'].items():
            if k['seen'] < 5 or k['seen'] < 0.05 * t['attacks']:
                continue
            rs = k['rec']
            ends = [r['lasts'] for r in rs if r['lasts'] is not None]
            fxs[key] = {'seen': k['seen'], 'delay': round(statistics.median(r['delay'] for r in rs), 3) if rs else 0.0,
                        'bound': most(r['bound'] for r in rs), 'target': most(r['target'] for r in rs),
                        'ended': round(len(ends) / max(1, len(rs)), 2),
                        'lasts': round(statistics.median(ends), 3) if ends and len(ends) * 2 >= len(rs) else None,
                        'bone': most(r['bone'] for r in rs), 'target_bone': most(r['target_bone'] for r in rs),
                        'flags': most(r['flags'] for r in rs), 'tag': most(r['tag'] for r in rs),
                        'scale': most(r['scale'] for r in rs), 'keyword': most(r['keyword'] for r in rs),
                        'bins': {b: [t['bins'][b], n] for b, n in k['bins'].items()}}
        if fxs:
            res[champ] = {'attacks': t['attacks'], 'fx': fxs}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'champions with attack effects ->', OUT)


if __name__ == '__main__':
    main()
