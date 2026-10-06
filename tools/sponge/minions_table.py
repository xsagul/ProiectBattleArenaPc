"""Lane minions of the replay for the test server: id, spawn and death time, kind, team, and their health over time.

kind from 98 +0x14 (04 melee -> 21 gold, 05 caster -> 14 gold in the replay's 453; cannon = 57 from SR_LevelScript),
team from the side of the map they spawn on (blue = x + z < 14000), health from the replay's replication (595,
lane minion group 3 bit 0). -> research/exe133/minions.json, research/exe133/minion_hp.pkl
"""
import collections
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, HERE)
import positions as PO  # noqa: E402
import replication as RP  # noqa: E402

CODEC = os.path.join(ROOT, 'research', 'exe133', 'codec')


def main():
    out = {}
    for line in open(os.path.join(CODEC, '98.all.jsonl')):
        r = json.loads(line)
        v = r['v']
        if not v:
            continue
        p = PO.at(r['obj'], r['t'] + 0.1)
        out[r['obj']] = {'spawn': r['t'], 'kind': {'04': 'melee', '05': 'caster'}.get(v['+0x14'], 'cannon'),
                         'wave': int(v['+0x15'], 16), 'team': 1 if p and p[0] + p[1] < 14000 else 0, 'death': None}
    for line in open(os.path.join(CODEC, '61.all.jsonl')):
        r = json.loads(line)
        if r['obj'] in out:
            out[r['obj']]['death'] = r['t']
    json.dump({str(k): v for k, v in out.items()}, open(os.path.join(ROOT, 'research', 'exe133', 'minions.json'), 'w'))
    hp = collections.defaultdict(list)
    for t, net, vals in RP.updates():
        if net in out and (3, 0) in vals:
            hp[net].append((t, RP.as_float(vals[(3, 0)])))
        if net in out and (3, 1) in vals:
            hp[('max', net)].append((t, RP.as_float(vals[(3, 1)])))
    pickle.dump(dict(hp), open(os.path.join(ROOT, 'research', 'exe133', 'minion_hp.pkl'), 'wb'))
    print(len(out), 'minions;', sum(1 for k in hp if not isinstance(k, tuple)), 'with health')


if __name__ == '__main__':
    main()
