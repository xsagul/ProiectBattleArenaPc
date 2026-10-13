"""How long the real server keeps each champion effect, from the replays: for every packet-10 instance a champion makes,
whether a 584 takes it away and when.

    python tools/fx_life16.py [n replays] [workers]     -> data/exe1620/fx_life16.json
        {champion: {key hex (or 'old:<+0x8>'): [made, ended by a 584, median life of the ended (s)]}}

The templates play an effect where the real server made one (core/templates.effect); it ends with a 584 after the
median life when at least half of the real ones did, else it ends by itself (no 584).
"""
import collections
import multiprocessing as mp
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'fx_life16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
        H = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    except Exception as x:
        return gid, {}, repr(x)
    made = {}
    ended = {}
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(10, 584)):
        if t > 1500:
            break
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if v is None:
            continue
        if pid == 10:
            for g in v.get('+0x10') or []:
                if not isinstance(g, dict):
                    continue
                key = g.get('+0x20') if g.get('+0x20') not in (None, '00000000') else 'old:' + str(g.get('+0x8'))
                for i in g.get('+0x10') or []:
                    if isinstance(i, dict) and u32(i.get('+0x18')) in H:
                        made[u32(i.get('+0x38'))] = (t, H[u32(i.get('+0x18'))], key)
        else:
            ended.setdefault(u32(v.get('+0x14')), t)
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    for eid, (t, champ, key) in made.items():
        e = ended.get(eid)
        out[champ][key].append(round(e - t, 3) if e is not None and e >= t else None)
    return gid, {c: dict(k) for c, k in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(lambda: collections.defaultdict(list))
    with mp.Pool(workers) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for c, ks in part.items():
                for k, xs in ks.items():
                    tot[c][k].extend(xs)
            print(gid, len(part), err, flush=True)
    res = {}
    for c, ks in sorted(tot.items()):
        res[c] = {}
        for k, xs in ks.items():
            ends = [x for x in xs if x is not None]
            res[c][k] = [len(xs), len(ends), round(statistics.median(ends), 3) if ends else None]
    import json
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'champions ->', OUT)


if __name__ == '__main__':
    main()
