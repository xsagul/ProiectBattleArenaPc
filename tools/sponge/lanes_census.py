"""Lane minions as Riot's server ran them in the replay, measured: the barracks that spawn them (98 +0x1c), each
barrack's team and lane, when in a wave each minion comes and of what kind, the lane paths they walk, their speed.
-> research/exe133/lanes.json (what our server's wave spawner uses)

  lanes_census.py
"""
import collections
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, HERE)
import positions as PO  # noqa: E402

CODEC = os.path.join(ROOT, 'research', 'exe133', 'codec')
OUT = os.path.join(ROOT, 'research', 'exe133', 'lanes.json')


def lane_of(pts):
    """top / mid / bot from where the path runs (SR: blue base bottom left, red top right)"""
    xs = [x for x, _ in pts]
    zs = [z for _, z in pts]
    mx, mz = statistics.mean(xs), statistics.mean(zs)
    if abs(mx - mz) < 2500:
        return 'mid'
    return 'top' if mz > mx else 'bot'


def main():
    rows = [json.loads(line) for line in open(os.path.join(CODEC, '98.all.jsonl'))]
    rows = [r for r in rows if r['v']]
    paths = PO.paths()
    barracks = collections.defaultdict(list)
    for r in rows:
        barracks[r['v']['+0x1c']].append(r)
    out = {'barracks': {}, 'note': 'measured from the 13.3 replay KR-6363178603 (98 = BarrackSpawnUnit)'}
    for bid, rs in barracks.items():
        rs.sort(key=lambda r: r['t'])
        first = rs[0]
        pts = []
        for t, p, sp in paths.get(first['obj'], [])[:12]:
            pts += p
        waves = collections.defaultdict(list)
        for r in rs:
            waves[int(r['v']['+0x15'], 16)].append(r)
        wave_rows = []
        for w, wr in sorted(waves.items()):
            t0 = wr[0]['t']
            wave_rows.append({'wave': w, 't': round(t0, 3),
                              'units': [[round(r['t'] - t0, 3), r['v']['+0x14'], r['v']['+0x16'], r['v']['+0x18'], r['v']['+0x20']] for r in wr]})
        spawn = paths.get(first['obj'], [[0, [(0, 0)]]])[0][1][0]
        team = 'blue' if spawn[0] + spawn[1] < 14000 else 'red'
        speeds = collections.Counter(round(sp) for r in rs[:30] for _, _, sp in paths.get(r['obj'], [])[:3])
        out['barracks'][bid] = {
            'team': team, 'lane': lane_of(pts) if pts else '?', 'first_path_point': [round(spawn[0]), round(spawn[1])],
            'speeds': dict(speeds.most_common(3)), 'waves': wave_rows[:12], 'n_waves': len(wave_rows),
            'example': {k: first['v'][k] for k in first['v']},
        }
    # each lane's path, base to base: a blue minion's walk to the meeting point, then a red one's reversed
    lanes = {}
    for lane in ('top', 'mid', 'bot'):
        halves = {}
        for bid, b in out['barracks'].items():
            if b['lane'] != lane:
                continue
            obj = barracks[bid][0]['obj']
            pts = []
            for t, p, sp in paths.get(obj, []):
                if pts and math.dist(pts[-1], p[0]) > 400:   # pulled off the lane (a fight): the lane walk ends
                    break
                pts += p[1:] if pts else p
                if len(pts) > 60:
                    break
            halves[b['team']] = [[round(x), round(z)] for x, z in pts]
        lanes[lane] = halves
    out['lane_walks'] = lanes
    json.dump(out, open(OUT, 'w'), indent=1)
    for bid, b in out['barracks'].items():
        w0 = b['waves'][0]
        print(bid, b['team'], b['lane'], 'waves', b['n_waves'], 'first', w0['t'], 'units', [(u[0], u[1]) for u in w0['units']],
              'speeds', b['speeds'])
    for w in out['barracks'][next(iter(out['barracks']))]['waves'][:8]:
        print('  wave', w['wave'], w['t'], [(u[0], u[1]) for u in w['units']])
    for lane, h in lanes.items():
        print(lane, {k: (len(v), v[:2], v[-1:]) for k, v in h.items()})


if __name__ == '__main__':
    main()
