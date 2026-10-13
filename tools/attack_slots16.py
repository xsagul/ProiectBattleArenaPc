"""Which attack variants each champion really uses, from the replays: 906's +0x10 +0xd is the attack's slot (0x40 +
the variant's index in basicAttack + extraAttacks, 0x49 the critical one; below 0x40 a spell's attack). The game's
own chances (mAttackProbability) hold for most champions, not for all [m: LeeSin 0.4 / 0.3 / 0.2 / 0.1 in the data,
only 0x40 in 323 attacks; Jinx 1 / 0 in the data, 95 / 88 in a replay].

    python tools/attack_slots16.py [n replays]    -> data/exe1620/attack_slots16.json {champion: {slot: count}}
"""
import collections
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'attack_slots16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
        H = R.heroes
    except Exception as x:
        return gid, {}, repr(x)
    out = collections.defaultdict(collections.Counter)
    seen, frame = set(), None
    for t, ch, pid, net, body, inc in R.flat(ids=(906,)):
        if net not in H:
            continue
        if t != frame:
            frame, seen = t, set()
        v = R.parse(pid, body)
        if not v:
            continue
        a = v.get('+0x10') or {}
        k = (net, a.get('+0x8'), a.get('+0x1c'))       # [m] the same attack once per observer: by its counter
        if k in seen:
            continue
        seen.add(k)
        try:
            out[H[net]['champion']][int(a.get('+0xd'), 16)] += 1
        except (TypeError, ValueError):
            pass
    return gid, {c: dict(x) for c, x in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 6
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(collections.Counter)
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for c, x in part.items():
                tot[c].update(x)
            print(gid, len(part), err, flush=True)
    json.dump({c: {f'{s:02x}': k for s, k in sorted(x.items())} for c, x in sorted(tot.items())}, open(OUT, 'w'), indent=0)
    print(len(tot), 'champions ->', OUT)


if __name__ == '__main__':
    main()
