"""How Riot's server fills the damage packet (150) for every spell and attack, read from the replays.

150 [m]: +0x10 amount, +0x14 target, +0x18 damage type (0 physical, 1 magic, 2 true), +0x19 a flag that is 1 for
most basic attacks (melee nearly always, ranged champions mostly 0), +0x1a the source kind (0 a direct hit - attack
or spell; 6 damage over time: Burning, MalzaharE, NasusE, LilliaP; 5 a pulsing area: GlacialStorm, JayceStaticField;
9 / 10 a missile out and back: AhriQ, ZiggsE; 4 QiyanaPassive; 7 an item's), +0x1c the source unit, +0x20 5 (2 =
critical), +0x2c the ELF hash of the spell's or the attack's name (a basic attack carries its own variant's name:
FioraBasicAttack2, SRU_OrderMinionRangedBasicAttack2, TurretBasicAttack).

    python tools/damage_rules16.py [n replays]    -> data/exe1620/damage_rules16.json
        {name hash (hex): [flag, source, the share of the majority, count]}
"""
import collections
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'damage_rules16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def scan(gid):
    import replaydb16
    R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    out = collections.defaultdict(collections.Counter)
    seen, frame = set(), None
    for t, ch, pid, net, body, inc in R.flat(ids=(150,)):
        if t > 900:
            break
        if t != frame:
            frame, seen = t, set()
        v = R.parse(pid, body)
        if not v:
            continue
        k = (net, json.dumps(v, sort_keys=True))     # [m] a replay holds a packet once per observer: the same content
        if k in seen:
            continue
        seen.add(k)
        h = int.from_bytes(bytes.fromhex(v['+0x2c']), 'little')
        if h:
            out[h][(int(v['+0x19'], 16), int(v['+0x1a'], 16))] += 1
    return gid, {h: dict(c) for h, c in out.items()}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(collections.Counter)
    with mp.Pool(4) as pool:
        for gid, part in pool.imap_unordered(scan, gids):
            for h, c in part.items():
                tot[h].update(c)
            print(gid, len(part), flush=True)
    rules = {}
    for h, c in tot.items():
        (flag, src), k = c.most_common(1)[0]
        n_all = sum(c.values())
        rules[f'{h:08x}'] = [flag, src, round(k / n_all, 3), n_all]
    json.dump(rules, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(rules), 'names ->', OUT)


if __name__ == '__main__':
    main()
