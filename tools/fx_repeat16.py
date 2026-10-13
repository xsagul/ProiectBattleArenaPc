"""How Riot's server takes an effect away: some effects get one 584, others the same 584 again frame after frame (Jinx's
minigun casts: ~20 in a row, 0.67 s) or twice in one frame. Per effect key, from the replays, the most common pattern
of 584s: the frame offsets from the first one.

[m: replay 4012247271, 90 - 900 s] 9,687 584s for 5,388 effects: 4,606 effects end with one, the rest with 2 - 30
(gaps of one frame, or 0: two in one frame); in the live recording (Garen + bots) almost all with one.

    python tools/fx_repeat16.py [n replays]     -> data/exe1620/fx_repeat16.json  {key hex | 'old:<+0x8>': [frame offsets]}
Only keys whose usual pattern is more than one 584 (and seen ended >= 5 times) are listed.
"""
import collections
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'fx_repeat16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    made, ends = {}, collections.defaultdict(list)
    seen = set()
    for t, ch, pid, net, body, inc in R.flat(ids=(10, 584)):
        if t > 1200:
            break
        k = (round(t, 4), pid, body, ch)
        if k in seen:
            continue                     # [m] a replay holds a packet once for every observer at one time
        seen.add(k)
        v = R.parse(pid, body)
        if v is None:
            continue
        if pid == 10:
            for g in v.get('+0x10') or []:
                if not isinstance(g, dict):
                    continue
                key = g.get('+0x20') if g.get('+0x20') not in (None, '00000000') else 'old:' + str(g.get('+0x8'))
                for i in g.get('+0x10') or []:
                    if isinstance(i, dict):
                        made[u32(i.get('+0x38'))] = key
        else:
            ends[u32(v.get('+0x14'))].append(round(t * 30))
    out = collections.defaultdict(collections.Counter)
    for e, fs in ends.items():
        key = made.get(e)
        if key is None:
            continue
        out[key][tuple(f - fs[0] for f in fs)] += 1
    return gid, {k: dict(c) for k, c in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(collections.Counter)
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for k, c in part.items():
                tot[k].update(c)
            print(gid, len(part), err, flush=True)
    res = {}
    for k, c in tot.items():
        if sum(c.values()) < 5:
            continue
        # the usual count of 584s, then the most common pattern of that count
        lens = collections.Counter()
        for p, m in c.items():
            lens[len(p)] += m
        size = lens.most_common(1)[0][0]
        if size < 2:
            continue
        pat = max((p for p in c if len(p) == size), key=lambda p: c[p])
        res[k] = list(pat)
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'effect keys taken away more than once ->', OUT)


if __name__ == '__main__':
    main()
