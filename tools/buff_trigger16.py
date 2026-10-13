"""Buffs Riot's server gives by an ITEM's or a RUNE's passive (or a champion's passive) - not by a cast: for every buff
given (435), the caster's event of that frame or just before (its basic attack hitting the buff's holder, its spell
hitting it, its attack beginning at it, its taking damage) and who owns it (the item every caster had, else the rune
every caster's page had, else the champion), from the replays.

  trigger   basic_hit / spell_hit / any_hit (caster damaged the holder), attack (caster began an attack at it),
            hurt (the holder - the caster itself - took damage), kill (the caster killed a unit)
  on        'target' (the unit hit) or 'self'
  cooldown  the shortest usual gap between two of the caster's applications (per holder), 10th percentile
  follows   share of the trigger's events (champion holders when the buff only goes on champions) followed by it while
            not on cooldown - kept only when the trigger both explains the 435s and is followed by them

    python tools/buff_trigger16.py [n replays]   -> data/exe1620/buff_trigger16.json
        {buff hash: {'owner': 'item:<id>' | 'rune:<id>' | champion, 'trigger', 'on', 'type', 'dur', 'count',
                     'cooldown', 'champions_only', 'explains', 'follows', 'n', 'name'}}
"""
import bisect
import collections
import json
import multiprocessing as mp
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'data', 'exe1620', 'buff_trigger16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
NEAR = 2
TRIGGERS = ('basic_hit', 'spell_hit', 'any_hit', 'attack', 'hurt')


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    import replay_golden16 as RG
    import elf_names16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    H = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    pages = RG.runes_of(R, set(H))
    items = collections.defaultdict(set)
    ev = collections.defaultdict(list)               # (caster, frame) -> [(kind, other unit)]
    casts = collections.defaultdict(set)
    adds = []
    names = {}
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 150, 906, 1215, 63)):
        if t > 1200:
            break
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if not v:
            continue
        f = round(t * 30)
        if pid == 63 and net in H:
            items[net].add(u32(v['+0x18']['+0x18']))
        elif pid == 150:
            src, h = u32(v.get('+0x1c')), v.get('+0x2c')
            if h not in names:
                names[h] = str(elf_names16.name(h) or '')
            basic = 'BasicAttack' in names[h] or 'CritAttack' in names[h]
            ev[(src, f)].append(('basic_hit' if basic else 'spell_hit', net))
            ev[(net, f)].append(('hurt', src))
        elif pid == 906 and net in H:
            a = v.get('+0x10') or {}
            ev[(net, f)].append(('attack', u32(a.get('+0x20')) if isinstance(a.get('+0x20'), str) else 0))
        elif pid == 1215 and net in H:
            casts[net].add(f)
        elif pid == 435:
            c = u32(v.get('+0x1c'))
            if c in H:
                adds.append((f, net, c, v['+0x64'], int(v['+0x38'], 16), round(struct.unpack('<f', bytes.fromhex(v['+0x3c']))[0], 2),
                             int(v.get('+0x40') or '01', 16), frozenset(items[c])))
    out = {}
    last = {}
    for f, holder, caster, h, btype, dur, count, its in adds:
        r = out.setdefault(h, {'n': 0, 'trig': collections.Counter(), 'on': collections.Counter(), 'meta': collections.Counter(),
                               'gaps': [], 'champs': collections.Counter(), 'items': None, 'runes': None, 'cast': 0,
                               'holder_hero': 0, 'events': collections.Counter(), 'followed': collections.Counter()})
        r['n'] += 1
        r['meta'][(btype, dur, count)] += 1
        r['champs'][H[caster]] += 1
        r['items'] = set(its) if r['items'] is None else (r['items'] & its)
        pg = set(pages.get(caster, []))
        r['runes'] = pg if r['runes'] is None else (r['runes'] & pg)
        r['holder_hero'] += holder in H
        r['on']['self' if holder == caster else 'target'] += 1
        if any(f - d in casts[caster] for d in range(0, NEAR + 1)):
            r['cast'] += 1
        found = set()
        for d in range(0, NEAR + 1):
            for kind, other in ev.get((caster, f - d), ()):
                if kind == 'hurt':
                    if holder == caster:
                        found.add('hurt')
                elif other == holder or holder == caster:
                    found.add(kind)
                    if kind in ('basic_hit', 'spell_hit'):
                        found.add('any_hit')
        for k in found:
            r['trig'][k] += 1
        k = (caster, holder, h)
        if k in last:
            r['gaps'].append((f - last[k]) / 30.0)
        last[k] = f
    # how often each trigger is followed by the buff (caster's events at champions when the buff goes on champions)
    by_caster = collections.defaultdict(list)
    for f, holder, caster, h, *_ in adds:
        by_caster[(caster, h)].append((f, holder))
    ev_of = collections.defaultdict(list)
    for (c, f), es in ev.items():
        if c in H:
            ev_of[c].append((f, es))
    for (caster, h), rows in by_caster.items():
        r = out[h]
        on_heroes = r['holder_hero'] >= 0.9 * r['n']
        fs = sorted(x[0] for x in rows)
        for f, es in ev_of.get(caster, ()):
            for kind, other in es:
                if on_heroes and kind != 'hurt' and other not in H:
                    continue
                kinds = [kind] + (['any_hit'] if kind in ('basic_hit', 'spell_hit') else [])
                i = bisect.bisect_left(fs, f)
                hit = i < len(fs) and fs[i] - f <= NEAR
                for kk in kinds:
                    r['events'][kk] += 1
                    r['followed'][kk] += hit
    res = {}
    for h, r in out.items():
        res[h] = {'n': r['n'], 'trig': dict(r['trig']), 'on': dict(r['on']), 'meta': {json.dumps(k): v for k, v in r['meta'].items()},
                  'gaps': r['gaps'][:500], 'champs': dict(r['champs']), 'items': sorted(r['items'] or ()), 'runes': sorted(r['runes'] or ()),
                  'cast': r['cast'], 'holder_hero': r['holder_hero'], 'events': dict(r['events']), 'followed': dict(r['followed'])}
    return gid, res, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, r in part.items():
                t = tot.setdefault(h, {'n': 0, 'trig': collections.Counter(), 'on': collections.Counter(), 'meta': collections.Counter(),
                                       'gaps': [], 'champs': collections.Counter(), 'items': None, 'runes': None, 'cast': 0,
                                       'holder_hero': 0, 'events': collections.Counter(), 'followed': collections.Counter()})
                for k in ('n', 'cast', 'holder_hero'):
                    t[k] += r[k]
                for k in ('trig', 'on', 'meta', 'champs', 'events', 'followed'):
                    t[k].update(r[k])
                t['gaps'] += r['gaps']
                t['items'] = set(r['items']) if t['items'] is None else (t['items'] & set(r['items']))
                t['runes'] = set(r['runes']) if t['runes'] is None else (t['runes'] & set(r['runes']))
            print(gid, len(part), err, flush=True)
    import elf_names16
    res = {}
    for h, t in tot.items():
        if t['n'] < 10 or t['cast'] > 0.5 * t['n']:
            continue                                     # a cast's buff: the templates give it
        best = None
        for k in TRIGGERS:
            explains = t['trig'].get(k, 0) / t['n']
            follows = t['followed'].get(k, 0) / max(1, t['events'].get(k, 0))
            if explains >= 0.7 and (best is None or explains > best[1] + 0.05 or (abs(explains - best[1]) <= 0.05 and follows > best[2])):
                best = (k, explains, follows)
        if best is None:
            continue
        top, top_n = max(t['champs'].items(), key=lambda kv: kv[1])
        its = sorted(i for i in (t['items'] or ()) if 1000 <= i < 9000 and i not in (2003, 2055, 3340, 3363, 3364))
        rns = sorted(i for i in (t['runes'] or ()) if i >= 8000 and i not in (5001, 5005, 5007, 5008, 5010, 5011, 5013))
        owner = top if top_n >= 0.9 * sum(t['champs'].values()) else ('item:%d' % its[0]) if its else \
            ('rune:%d' % rns[0]) if rns else 'any'
        (btype, dur, count), _ = max(((tuple(json.loads(k)), n) for k, n in t['meta'].items()), key=lambda kv: kv[1])
        gaps = sorted(t['gaps'])
        res[h] = {'owner': owner, 'trigger': best[0], 'explains': round(best[1], 2), 'follows': round(best[2], 2),
                  'on': max(t['on'].items(), key=lambda kv: kv[1])[0], 'type': btype, 'dur': dur, 'count': count,
                  'cooldown': round(gaps[len(gaps) // 10], 2) if len(gaps) >= 10 else 0.0,
                  'champions_only': t['holder_hero'] >= 0.9 * t['n'], 'n': t['n'], 'name': elf_names16.name(h)}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs given by a trigger ->', OUT)
    for h, r in sorted(res.items(), key=lambda kv: -kv[1]['n'])[:30]:
        print(f"  {str(r['name'] or h)[:34]:34s} {r['owner']:14s} {r['trigger']:9s} on {r['on']:6s} n {r['n']:5d} expl {r['explains']} "
              f"follows {r['follows']} cd {r['cooldown']} type {r['type']} dur {r['dur']}")


if __name__ == '__main__':
    main()
