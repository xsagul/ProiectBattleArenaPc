"""Animation overrides a champion's scripts set on every script update (904 S2C_SetAnimStates), from the replays: per
champion, how steady its 904 stream is and which content goes with which of its buffs.

    python tools/anim_states16.py [n replays]     -> data/exe1620/anim_states16.json
        {champion: {'stream': share of its script updates (while alive) with a 904, 'n': 904s seen,
                    'default': [[from, to], ...] the content with none of the rule buffs,
                    'rules': [[[buff hash hex, ...], [[from, to], ...]], ...] most specific first}}
A content's key buffs: present at >= 90 % of its 904s and at <= 25 % of the champion's other 904s. Hashes are the
replays' little-endian hex. Each pair is listed as the real server sends it (Aatrox: every pair twice).
"""
import collections
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'anim_states16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
T1 = 900.0


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    H = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    slots = collections.defaultdict(dict)        # hero -> slot -> hash
    samples = collections.defaultdict(list)      # champion -> [(content, frozenset buffs)]
    times = collections.defaultdict(list)
    dead = collections.defaultdict(list)
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 904, 421)):
        if t > T1:
            break
        if net not in H:
            continue
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if v is None:
            continue
        if pid == 435:
            slots[net][v['+0x60']] = v['+0x64']
        elif pid == 262:
            slots[net].pop(v['+0x10'], None)
        elif pid == 421:
            dead[net].append(t)
        elif pid == 904:
            content = tuple((e['+0x8'], e['+0xc']) for e in v['+0x10'])
            samples[H[net]].append((content, frozenset(slots[net].values())))
            times[H[net]].append(t)
    out = {}
    for c, s in samples.items():
        ts = sorted(set(round(t, 3) for t in times[c]))
        span = (min(T1, ts[-1]) - 90.0) if ts else 0
        steady = sum(1 for t in ts if t >= 90.0)
        out[c] = {'samples': [(list(map(list, a)), sorted(b)) for a, b in s], 'steady': steady, 'span': span}
    return gid, out, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 128
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    allc = collections.defaultdict(list)
    rate = collections.defaultdict(list)
    with mp.Pool(int(os.environ.get('WORKERS', '4'))) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for c, r in part.items():
                allc[c] += [(tuple(map(tuple, a)), frozenset(b)) for a, b in r['samples']]
                if r['span'] > 60:
                    rate[c].append(r['steady'] / (r['span'] / 0.2673))
            print(gid, len(part), err, flush=True)
    res = {}
    for c, s in allc.items():
        stream = sorted(rate[c])[len(rate[c]) // 2] if rate[c] else 0.0
        if stream < 0.5 or len(s) < 200:
            continue
        by = collections.Counter(a for a, b in s)
        contents = [a for a, k in by.most_common() if k >= max(20, 0.02 * len(s))]
        rules, default = [], None
        for a in contents:
            mine = [b for x, b in s if x == a]
            other = [b for x, b in s if x != a]
            cnt = collections.Counter(h for b in mine for h in b)
            key = sorted(h for h, k in cnt.items() if k >= 0.9 * len(mine) and
                         sum(1 for b in other if h in b) <= 0.25 * max(1, len(other)))
            if key:
                rules.append([key, [list(p) for p in a]])
            elif default is None:
                default = [list(p) for p in a]
        rules.sort(key=lambda r: -len(r[0]))
        res[c] = {'stream': round(stream, 2), 'n': len(s), 'default': default, 'rules': rules}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'champions with a 904 stream ->', OUT)
    for c, r in sorted(res.items(), key=lambda kv: -kv[1]['n']):
        print(c, r['stream'], r['n'], 'rules', len(r['rules']), 'default', bool(r['default']))


if __name__ == '__main__':
    main()
