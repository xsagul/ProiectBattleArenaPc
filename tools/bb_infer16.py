"""What each buff of a champion does, read from the replays' evidence (tools/bb_evidence16.py) - the facts a
BuildingBlocks script of it has to reproduce -> data/bb16/infer/<Champion>.json

    python tools/bb_infer16.py <Champion> [..]            (prints the summary too)

For every buff name the champion gives (to itself or to others), over all its instances:
  given_by     what happened in the frame of the 435 (or up to 0.3 s before): a cast of a spell (name), the holder's or
               the giver's attack hit / spell hit (the damage's name), another buff of the champion ending
  duration     the duration sent, by the champion's level of that spell (the cast's rank is not in the replay: by the
               champion's level and the duration's clusters)
  ends         'time' (it lived its duration) or the event in its last frame: the holder's attack hit, a cast, death
  ticks        damage / heals named like it while it lasts, and their period
  on_hit       what the holder's attack hits do while it lasts that they do not do otherwise (damage names, buffs given)
  at_add / at_end   the champion's other packets in the frames it begins / ends (effects, slot spells, cooldowns)
Each fact carries how many instances showed it (share): a script gets it when the share is high, as a condition when
it is middling.
"""
import collections
import glob
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)

EVID = os.path.join(ROOT, 'data', 'bb16', 'evidence')
OUT = os.path.join(ROOT, 'data', 'bb16', 'infer')
NAMES = os.path.join(ROOT, 'data', 'bb16', 'script_names.json')
_names = None


def name_of(h):
    global _names
    if _names is None:
        _names = json.load(open(NAMES))
        try:
            import elf_names16
            _names_extra = elf_names16
        except Exception:
            _names_extra = None
        _names['_x'] = _names_extra
    n = _names.get(f'{h:08x}')
    if n:
        return n
    ex = _names.get('_x')
    if ex is not None:
        try:
            m = ex.name(h)
            if m:
                return m
        except Exception:
            pass
    return f'#{h:08x}'


class index:
    """rows sorted by time, searched by bisection"""
    def __init__(self, rows, key=0):
        self.rows = sorted(rows, key=lambda r: r[key])
        self.ts = [r[key] for r in self.rows]


def near(by_t, t, lo, hi):
    """rows of by_t within [t+lo, t+hi]"""
    import bisect
    i = bisect.bisect_left(by_t.ts, t + lo - 1e-6)
    j = bisect.bisect_right(by_t.ts, t + hi + 1e-6)
    return by_t.rows[i:j]


def games_with(champ):
    for p in sorted(glob.glob(os.path.join(EVID, '*.pkl'))):
        d = pickle.load(open(p, 'rb'))
        nets = [n for n, c in d['heroes'].items() if c == champ]
        if nets:
            yield d, nets[0]


def new_facts():
    return collections.defaultdict(lambda: {'n': 0, 'self': 0, 'type': collections.Counter(), 'dur': collections.Counter(),
                                            'given_by': collections.Counter(), 'ends': collections.Counter(),
                                            'ticks': collections.Counter(), 'period': [], 'on_hit': collections.Counter(),
                                            'at_add': collections.Counter(), 'at_end': collections.Counter(), 'lived': []})


def game_facts(path):
    """one replay -> {champion: facts of its buffs in that game} (every champion of the game in one pass)"""
    d = pickle.load(open(path, 'rb'))
    out = {}
    for me, champ in d['heroes'].items():
        facts = new_facts()
        hero_facts(d, me, facts)
        out[champ] = {k: dict(v) for k, v in facts.items()}
    return out


def merge(into, part):
    for name, f in part.items():
        g = into[name]
        for k, v in f.items():
            if isinstance(v, collections.Counter):
                g[k].update(v)
            elif isinstance(v, list):
                g[k] += v
            else:
                g[k] += v


def hero_facts(d, me, facts):
    casts = [c for c in d.get('casts', []) if c[1] == me]
    cast_t = sorted(casts)
    hits_by_me = [h for h in d.get('hits', []) if h[2] == me]
    hits_t = index(hits_by_me)
    attacks_me = index([a for a in d.get('attacks', []) if a[1] == me])
    mine_fx = index([e for e in d.get('effects', []) if e[2] == me or e[3] == me])
    gone = {}
    for t_, fid in d.get('fx_gone', []):
        gone.setdefault(fid, t_)
    slots = index([s for s in d.get('slots', []) if s[1] == me])
    cds = index([c for c in d.get('cooldowns', []) if c[1] == me])
    deaths = {r[1]: r[0] for r in d.get('deaths', [])}
    heals = [h for h in d.get('heals', []) if h[1] == me]
    buffs = [b for b in d['buffs'] if b['caster'] == me or b['holder'] == me]
    ends_t = index([(b['removed'], name_of(b['hash'])) for b in buffs if b['removed'] is not None and b['holder'] == me])
    for b in buffs:
        name = name_of(b['hash'])
        f = facts[name]
        f['n'] += 1
        f['self'] += b['holder'] == me
        f['type'][b['type']] += 1
        f['dur'][b['duration']] += 1
        t0 = b['added']
        # given by: a cast within 0.3 s before, a hit of mine in the frame, another of my buffs ending in the frame
        cs = [c for c in cast_t if t0 - 0.3 <= c[0] <= t0 + 0.001]
        if cs:
            f['given_by'][('cast', name_of(cs[-1][2]))] += 1
        for h in near(hits_t, t0, -0.001, 0.001):
            f['given_by'][('hit', name_of(h[5]))] += 1
        for e in near(ends_t, t0, -0.001, 0.001):
            if e[1] != name:
                f['given_by'][('end', e[1])] += 1
        if not cs and not near(hits_t, t0, -0.001, 0.001):
            f['given_by'][('none',)] += 1
        # its end
        t1 = b['removed']
        if t1 is not None:
            f['lived'].append(round(t1 - t0, 3))
            if b['duration'] < 20000 and abs(t1 - t0 - b['duration']) <= 0.3:
                f['ends'][('time',)] += 1
            else:
                holder_hits = [h for h in near(hits_t, t1, -0.001, 0.001)] if b['holder'] == me else []
                if holder_hits:
                    f['ends'][('my hit', name_of(holder_hits[0][5]))] += 1
                elif [c for c in cast_t if t1 - 0.05 <= c[0] <= t1 + 0.001]:
                    f['ends'][('my cast', name_of([c for c in cast_t if t1 - 0.05 <= c[0] <= t1 + 0.001][-1][2]))] += 1
                elif deaths.get(b['holder']) is not None and abs(deaths[b['holder']] - t1) < 0.05:
                    f['ends'][('death',)] += 1
                else:
                    f['ends'][('other',)] += 1
            for e in near(mine_fx, t1, -0.001, 0.001):
                f['at_end'][('fx', e[1])] += 1
            for s in near(slots, t1, -0.001, 0.001):
                f['at_end'][('slot', s[2], s[3])] += 1
        for e in near(mine_fx, t0, -0.001, 0.001):
            f['at_add'][('fx', e[1])] += 1
            g_ = gone.get(e[4])
            if t1 is not None and g_ is not None and abs(g_ - t1) <= 0.05:
                f['at_add'][('fx_until_end', e[1])] += 1
        for s in near(slots, t0, -0.001, 0.001):
            f['at_add'][('slot', s[2], s[3])] += 1
        for c in near(cds, t0, -0.001, 0.001):
            f['at_add'][('cooldown', c[2])] += 1
        # while it lasts: damage named like it (its ticks), my attack hits' extra damage names
        end = t1 if t1 is not None else t0 + min(b['duration'], 60.0)
        named = [h for h in hits_by_me if t0 < h[0] <= end and name_of(h[5]) == name]
        for h in named:
            f['ticks'][h[4]] += 1
        ts = sorted({round(h[0], 2) for h in named})
        f['period'] += [round(b2 - a2, 3) for a2, b2 in zip(ts, ts[1:])]
        if b['holder'] == me:
            for h in hits_by_me:
                if t0 < h[0] <= end and name_of(h[5]) not in (name,):
                    att = near(attacks_me, h[0], -2.0, 0.0)
                    if att:
                        f['on_hit'][name_of(h[5])] += 1


def infer_all(champs=None, workers=6):
    """every champion's facts (or only those named) -> {champion: facts, games}"""
    from multiprocessing import Pool
    paths = sorted(glob.glob(os.path.join(EVID, '*.pkl')))
    total, games = collections.defaultdict(new_facts), collections.Counter()
    with Pool(workers) as P:
        for part in P.imap_unordered(game_facts, paths):
            for champ, f in part.items():
                if champs and champ not in champs:
                    continue
                games[champ] += 1
                merge(total[champ], f)
    return total, games


def summarise(facts, n_games):
    out = {}
    for name, f in facts.items():
        n = f['n']
        per = sorted(f['period'])
        out[name] = {
            'n': n, 'games': n_games, 'self': round(f['self'] / n, 3),
            'type': f['type'].most_common(1)[0][0],
            'durations': [[d, c] for d, c in f['dur'].most_common(6)],
            'given_by': [[list(k), round(c / n, 3)] for k, c in f['given_by'].most_common(6)],
            'ends': [[list(k), round(c / max(1, len(f['lived'])), 3)] for k, c in f['ends'].most_common(5)],
            'lived_med': sorted(f['lived'])[len(f['lived']) // 2] if f['lived'] else None,
            'ticks': sum(f['ticks'].values()), 'period_med': per[len(per) // 2] if per else None,
            'on_hit': [[k, c] for k, c in f['on_hit'].most_common(5)],
            'at_add': [[list(k), round(c / n, 3)] for k, c in f['at_add'].most_common(6)],
            'at_end': [[list(k), round(c / n, 3)] for k, c in f['at_end'].most_common(6)],
        }
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    champs = [a for a in sys.argv[1:] if not a.startswith('--')]
    total, games = infer_all(set(champs) if champs else None)
    for champ in sorted(total):
        res = summarise(total[champ], games[champ])
        json.dump(res, open(os.path.join(OUT, f'{champ}.json'), 'w'), indent=1)
        if not champs:
            continue
        print(f'== {champ}: {len(res)} buffs')
        for name, r in sorted(res.items(), key=lambda x: -x[1]['n'])[:25]:
            print(f"{r['n']:4d} {name:34s} self {r['self']:.2f} type {r['type']:2d} dur {r['durations'][:3]} lived {r['lived_med']}")
            print(f"       given {r['given_by'][:3]}  ends {r['ends'][:3]}")
            if r['ticks'] or r['on_hit'] or r['at_add'] or r['at_end']:
                print(f"       ticks {r['ticks']} every {r['period_med']}  on_hit {r['on_hit'][:3]}  add {r['at_add'][:3]}  end {r['at_end'][:3]}")


if __name__ == '__main__':
    main()
