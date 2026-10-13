"""What makes Riot's server renew a buff (282 NPC_BuffUpdateCount), from the replays: for every 282 of a buff, which event
of the buff's caster (or holder) came in the same frame or just before, and for every such event while the buff was on,
whether a 282 followed - so a cause is kept only when it both explains the 282s and is followed by one.

  causes   attack     the caster began a basic attack (906)
           basic_hit  the caster's basic attack damaged a unit (150 with an attack name)
           spell_hit  the caster's spell damaged a unit (150, other names)
           cast       the caster cast a spell (1215)
           hurt       the holder took damage (150 to it)
           tick       none of these: one script update (8 frames) after the last 282 / the 435
           frame      1 - 2 frames after the last 282 (its value: the gap in frames)
[m: 4 replays] Jinx's Q stacks (40f7f805) renew at her attacks, Kindred's 5504d50b at hits, Ekko's a7a52602 every update.

    python tools/buff_renew16.py [n replays]   -> data/exe1620/buff_renew16.json
        {buff hash: {'causes': {cause: delay in frames after the event}, 'explains' (share of its 282s the causes
         explain), 'n', 'dur' (the duration a 282 sets: most common), 'count' (most common count),
         'counts' (distinct counts seen: 1 = fixed)}}
"""
import collections
import json
import multiprocessing as mp
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'buff_renew16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
BASE = ('attack', 'basic_hit', 'spell_hit', 'cast', 'hurt', 'tick', 'frame')
# a caster's event can count only when it is about the buff's holder (@holder) or a champion (@hero)
SCOPED = ('attack', 'basic_hit', 'spell_hit')
CAUSES = BASE + tuple(f'{c}@{s}' for c in SCOPED for s in ('holder', 'hero'))
NEAR = 2                         # frames: an event this close before the 282 explains it
NEAR_CAUSE = {'attack': 12, 'attack@holder': 12, 'attack@hero': 12}      # an attack renews at its windup's end (the 906 is its start)


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    import elf_names16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    ev = collections.defaultdict(set)            # (unit, frame) -> {(cause, the other unit)}
    heroes = {n for n in R.heroes if n < 0x40000100}
    live = {}                                    # (holder, slot) -> [hash, caster, f0, last 282 frame, [282 frames], vals]
    lives = []
    frame, seen = None, set()
    names = {}
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 282, 906, 1215, 150)):
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
        if pid == 906:
            a = v.get('+0x10') or {}
            ev[(net, f)].add(('attack', u32(a.get('+0x20')) if isinstance(a.get('+0x20'), str) else 0))
        elif pid == 1215:
            ev[(net, f)].add(('cast', 0))
        elif pid == 150:
            src, h = u32(v.get('+0x1c')), v.get('+0x2c')
            if h not in names:
                names[h] = str(elf_names16.name(h) or '')
            nm = names[h]
            ev[(src, f)].add(('basic_hit' if ('BasicAttack' in nm or 'CritAttack' in nm) else 'spell_hit', net))
            ev[(net, f)].add(('hurt', src))
        elif pid == 435:
            k = (net, v['+0x60'])
            if k in live:
                lives.append(live.pop(k) + [f])
            live[k] = [v['+0x64'], u32(v.get('+0x1c')), f, [], [], net]
        elif pid == 262:
            k = (net, v['+0x10'])
            if k in live:
                lives.append(live.pop(k) + [f])
        else:
            k = (net, v['+0x18'])
            if k in live:
                live[k][3].append(f)
                live[k][4].append((round(struct.unpack('<f', bytes.fromhex(v['+0x10']))[0], 3), int(v['+0x20'], 16)))
    for k, x in live.items():
        lives.append(x + [frame and round(frame * 30) or 0])
    out = {}
    for h, caster, f0, fs, vals, holder, f1 in lives:
        r = out.setdefault(h, {'n': 0, 'expl': collections.Counter(), 'delay': collections.defaultdict(collections.Counter),
                               'causes': collections.Counter(), 'followed': collections.Counter(), 'vals': collections.Counter(),
                               'sets': collections.Counter()})
        r['n'] += len(fs)
        r['vals'].update(vals)
        prev = f0
        got = set(fs)
        for f in fs:
            found = set()
            for d in range(0, max(NEAR, max(NEAR_CAUSE.values())) + 1):
                for c, other in ev.get((caster, f - d), ()):
                    if c == 'hurt' or d > NEAR_CAUSE.get(c, NEAR):
                        continue
                    names_ = [c] + ([f'{c}@holder'] if c in SCOPED and other == holder and holder != caster else []) +                         ([f'{c}@hero'] if c in SCOPED and other in heroes else [])
                    for nm_ in names_:
                        if nm_ not in found:
                            found.add(nm_)
                            r['delay'][nm_][d] += 1
                if d <= NEAR and any(c == 'hurt' for c, o in ev.get((holder, f - d), ())) and 'hurt' not in found:
                    found.add('hurt')
                    r['delay']['hurt'][d] += 1
            if abs((f - prev) - 8) <= 1:
                found.add('tick')
                r['delay']['tick'][0] += 1
            elif 1 <= f - prev <= 2:
                found.add('frame')                       # renewed every frame or every other one: the delay holds the gap
                r['delay']['frame'][f - prev] += 1
            for c in found:
                r['expl'][c] += 1
            r['sets'][tuple(sorted(found))] += 1
            prev = f
        # causes during the buff's life (after its first frame) and whether a 282 followed within NEAR frames
        for f in range(f0 + 1, f1):
            for c, other in ev.get((caster, f), ()):
                if c == 'hurt':
                    continue
                names_ = [c] + ([f'{c}@holder'] if c in SCOPED and other == holder and holder != caster else []) +                     ([f'{c}@hero'] if c in SCOPED and other in heroes else [])
                hit = any((f + d) in got for d in range(0, NEAR_CAUSE.get(c, NEAR) + 1))
                for nm_ in names_:
                    r['causes'][nm_] += 1
                    r['followed'][nm_] += hit
            if any(c == 'hurt' for c, o in ev.get((holder, f), ())):
                r['causes']['hurt'] += 1
                if any((f + d) in got for d in range(0, NEAR + 1)):
                    r['followed']['hurt'] += 1
    return gid, {h: {'n': r['n'], 'expl': dict(r['expl']), 'delay': {c: dict(d) for c, d in r['delay'].items()},
                     'causes': dict(r['causes']), 'followed': dict(r['followed']),
                     'sets': {'|'.join(k): n for k, n in r['sets'].items()},
                     'vals': {f'{a}|{b}': n for (a, b), n in r['vals'].items()}} for h, r in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, r in part.items():
                t = tot.setdefault(h, {'n': 0, 'expl': collections.Counter(), 'delay': collections.defaultdict(collections.Counter),
                                       'causes': collections.Counter(), 'followed': collections.Counter(), 'vals': collections.Counter(),
                                       'sets': collections.Counter()})
                t['n'] += r['n']
                t['sets'].update(r['sets'])
                for k in ('expl', 'causes', 'followed', 'vals'):
                    t[k].update(r[k])
                for c, d in r['delay'].items():
                    t['delay'][c].update({int(x): y for x, y in d.items()})
            print(gid, len(part), err, flush=True)
    res = {}
    for h, t in tot.items():
        if t['n'] < 20:
            continue
        # the causes: each followed by a 282 most of the time; picked by what they explain until 80 % of the 282s are
        ok = [c for c in CAUSES if (1.0 if c in ('tick', 'frame') else t['followed'].get(c, 0) / max(1, t['causes'].get(c, 0))) >= 0.6]
        chosen, covered = [], 0.0
        while True:
            def union(cs):
                return sum(n for k, n in t['sets'].items() if any(c in k.split('|') for c in cs)) / t['n']
            rest = [c for c in ok if c not in chosen]
            if not rest or covered >= 0.8:
                break
            c = max(rest, key=lambda c: union(chosen + [c]))
            gain = union(chosen + [c]) - covered
            if gain < 0.1:
                break
            chosen.append(c)
            covered = union(chosen)
        if covered < 0.6:
            continue
        best = (chosen[0], covered, 0.0)
        c = best[0]
        (dur, count), _ = max(((k.split('|')[0], k.split('|')[1]), n) for k, n in t['vals'].items())[:1] and \
            max(((tuple(k.split('|')), n) for k, n in t['vals'].items()), key=lambda kv: kv[1])
        res[h] = {'causes': {c: t['delay'][c].most_common(1)[0][0] if t['delay'][c] else 0 for c in chosen},
                  'explains': round(covered, 2), 'n': t['n'], 'dur': float(dur),
                  'count': int(count), 'counts': len({k.split('|')[1] for k in t['vals']})}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs with renewal causes ->', OUT, collections.Counter(c for r in res.values() for c in r['causes']))


if __name__ == '__main__':
    main()
