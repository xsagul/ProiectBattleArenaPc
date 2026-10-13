"""Which champions play better on their BuildingBlocks scripts (data/bb16/scripts, tools/bb_write16.py) than on the
replays' templates: the golden test of each replay twice, the champions' own packets compared -> data/bb16/choice.json

    python tools/golden_bb16.py [n replays] [--workers k]     -> data/bb16/choice.txt (per champion: packets of its
                                                                own paired with templates / with scripts)
    BB_CHAMPS=@choice python tools/replay_golden16.py batch ...   then plays the chosen ones on their scripts

A champion's own packets = the replay's packets whose net id is the champion (its buffs, casts, slots ...). A champion
is chosen when its scripts pair at least as many of them as the templates over every replay it is in.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'bb16')


def own_pairs(theirs, ours, heroes, window=0.15):
    """per hero net: (replay count, paired count) of the packets about it"""
    import bisect
    by = collections.defaultdict(list)
    for x in ours:
        if x[2] in heroes:
            by[(x[1], x[2])].append(x[0])
    for k in by:
        by[k].sort()
    used = collections.defaultdict(set)
    rep, par = collections.Counter(), collections.Counter()
    for x in sorted(theirs):
        if x[2] not in heroes:
            continue
        rep[x[2]] += 1
        lst = by.get((x[1], x[2]), [])
        i = bisect.bisect_left(lst, x[0] - window)
        while i < len(lst) and lst[i] <= x[0] + window:
            if i not in used[(x[1], x[2])]:
                used[(x[1], x[2])].add(i)
                par[x[2]] += 1
                break
            i += 1
    return rep, par


def one(args):
    gid, mode = args
    if mode == 'bb':
        os.environ['BB_CHAMPS'] = 'ALL'
    else:
        os.environ.pop('BB_CHAMPS', None)
    import replay_golden16 as G
    theirs, ours, stats, heroes, champs, logs = G.run(gid, 90, 900)
    rep, par = own_pairs(theirs, ours, heroes)
    import replaydb16
    R = replaydb16.Replay(os.path.join(ROOT, 'data', 'replays16', 'rofl', f'{gid}.rofl'))
    names = {n: h['champion'] for n, h in R.heroes.items() if n in heroes}
    return gid, mode, {names[n]: (rep[n], par[n]) for n in heroes if n in names}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    n = int(args[0]) if args else 12
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 6
    # the golden batch's replays: the first n at hand (replay_golden16.batch)
    ids = sorted(f[:-5] for f in os.listdir(os.path.join(ROOT, 'data', 'replays16', 'rofl')) if f.endswith('.rofl'))[:n]
    from multiprocessing import Pool
    res = collections.defaultdict(lambda: {'tpl': [0, 0], 'bb': [0, 0]})
    with Pool(workers) as P:
        for gid, mode, per in P.imap_unordered(one, [(g, m) for g in ids for m in ('tpl', 'bb')]):
            for champ, (r, p) in per.items():
                res[champ][mode][0] += r
                res[champ][mode][1] += p
            print(gid, mode, 'done', flush=True)
    chosen = sorted(c for c, v in res.items() if v['bb'][1] >= v['tpl'][1] and v['bb'][1] > 0)
    lines = [f'{len(chosen)} of {len(res)} champions play at least as well on their scripts', '']
    for c, v in sorted(res.items(), key=lambda x: x[1]['bb'][1] - x[1]['tpl'][1], reverse=True):
        r, pt, pb = v['tpl'][0], v['tpl'][1], v['bb'][1]
        lines.append(f'{"BB " if c in chosen else "tpl"} {c:14s} own {r:6d}  templates {pt:6d} ({100 * pt / max(1, r):5.1f} %)  '
                     f'scripts {pb:6d} ({100 * pb / max(1, r):5.1f} %)')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'choice.txt'), 'w').write('\n'.join(lines) + '\n')
    json.dump(chosen, open(os.path.join(OUT, 'choice.json'), 'w'))
    print('\n'.join(lines[:3]), '->', os.path.join(OUT, 'choice.txt'))


if __name__ == '__main__':
    main()
