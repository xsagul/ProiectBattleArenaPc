"""Minion facts from real Riot server replays (maknee's decoded packets, patch 13.2): wave spawn timing, minion vs
minion / champion / turret damage values and the time between one minion's hits, turret shots on minions.

    python tools/replay13_minions.py data/replays/maknee13_2/batch_001.jsonl.gz [matches]
"""
import collections
import gzip
import json
import statistics
import sys

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 8

spawn_gaps = collections.Counter()      # seconds between minions of one wave from one barrack
wave_starts = collections.Counter()     # first minion of wave n (time)
wave_period = collections.Counter()
hits = collections.defaultdict(list)    # (source kind, target kind) -> damage values
intervals = collections.defaultdict(list)  # source kind -> seconds between consecutive hits of one source
first_damage = []

with gzip.open(path, 'rt', encoding='utf-8') as f:
    for mi, line in enumerate(f):
        if mi >= limit:
            break
        ev = json.loads(line)['events']
        kind = {}
        per_barrack = collections.defaultdict(lambda: collections.defaultdict(list))
        last_hit = {}
        for e in ev:
            k = next(iter(e)); d = e[k]
            if k == 'CreateHero':
                kind[d['net_id']] = 'hero'
            elif k == 'CreateTurret':
                kind[d['net_id']] = 'turret'
            elif k == 'CreateNeutral':
                kind[d['net_id']] = 'neutral'
            elif k == 'BarrackSpawnUnit':
                kind[d['minion_net_id']] = 'minion'
                per_barrack[d['barrack_net_id']][d['wave_count']].append(d['time'])
            elif k == 'UnitApplyDamage':
                s, t = d['source_net_id'], d['target_net_id']
                ks, kt = kind.get(s, '?'), kind.get(t, '?')
                hits[(ks, kt)].append(round(d['damage'], 2))
                if s in last_hit and ks == 'minion':
                    gap = d['time'] - last_hit[s]
                    if 0.2 < gap < 3:
                        intervals[ks].append(round(gap, 3))
                last_hit[s] = d['time']
        for b, waves in per_barrack.items():
            starts = []
            for w, times in sorted(waves.items()):
                times.sort()
                starts.append(times[0])
                for a, c in zip(times, times[1:]):
                    spawn_gaps[round(c - a, 2)] += 1
                if w <= 3:
                    wave_starts[(w, round(times[0], 1))] += 1
            for a, c in zip(starts, starts[1:]):
                wave_period[round(c - a, 1)] += 1

print('== waves')
print('first minion of waves 1-3 (wave, time): ', sorted(wave_starts.items())[:12])
print('seconds between waves:', wave_period.most_common(8))
print('seconds between minions of one wave:', spawn_gaps.most_common(10))
print('== damage values (most common) per source -> target')
for key, vals in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:10]:
    c = collections.Counter(vals).most_common(10)
    print(f'{key[0]:>7} -> {key[1]:<7} n={len(vals):6d}  {c}')
print('== seconds between consecutive hits of one minion')
for ks, v in intervals.items():
    c = collections.Counter(round(x, 2) for x in v).most_common(10)
    print(ks, 'n', len(v), 'median', statistics.median(v), c)
