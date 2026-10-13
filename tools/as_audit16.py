"""Our champions' bonus attack speed against the real one, second by second: the replay replicates every champion's
mPercentAttackSpeedMod (287, AIHero) and mPercentMultiplicativeAttackSpeedMod; the golden test with GOLDEN_AS=1 logs
ours (golden16/as_<gid>.json). Where a champion's attack speed is short, some rune / item / ability is not played.

    GOLDEN_AS=1 python tools/replay_golden16.py <gid> --from 90 --to 900     (or batch)
    python tools/as_audit16.py [gid ...]          -> per champion: real / ours mean, median gap, share of seconds short
"""
import bisect
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)
import replay_golden16 as RG  # noqa: E402


def real_series(R, heroes, t1):
    import replication
    import repl16
    out = collections.defaultdict(list)          # net -> [(t, bonus, multiplicative)]
    for t, ch, pid, net, body, inc in R.flat(ids=(287,)):
        if t > t1:
            break
        v = R.parse(pid, body)
        try:
            units = replication.parse(bytes.fromhex(v['+0x20']['text']))
        except Exception:
            continue
        for n, groups in units:
            if n not in heroes:
                continue
            vals = repl16.read_unit(groups, 'AIHero')
            if 'mPercentAttackSpeedMod' in vals or 'mPercentMultiplicativeAttackSpeedMod' in vals:
                last = out[n][-1] if out[n] else (0.0, 0.0, 1.0)
                out[n].append((t, vals.get('mPercentAttackSpeedMod', last[1]),
                               vals.get('mPercentMultiplicativeAttackSpeedMod', last[2]) or 1.0))
    return out


def audit(gid):
    import replaydb16 as RD
    path = os.path.join(RG.OUT, f'as_{gid}.json')
    if not os.path.exists(path):
        return {}
    ours = json.load(open(path))
    R = RD.Replay(os.path.join(RG.DATA, 'rofl', f'{gid}.rofl'))
    names = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    real = real_series(R, set(names), max(x[0] for x in ours) + 1)
    rows = collections.defaultdict(list)
    for t, n, bonus, level, alive in ours:
        s = real.get(n)
        if not s or not alive:
            continue
        i = bisect.bisect_right([x[0] for x in s], t) - 1
        if i < 0:
            continue
        rb, rm = s[i][1], s[i][2]
        rows[names[n]].append((rb, bonus, rm))
    return rows


def main():
    gids = sys.argv[1:] or sorted(f[3:-5] for f in os.listdir(RG.OUT) if f.startswith('as_') and f.endswith('.json'))
    tot = collections.defaultdict(list)
    for gid in gids:
        for champ, r in audit(gid).items():
            tot[champ] += r
    print(f'{"champion":14s} {"n":>5} {"real":>6} {"ours":>6} {"median gap":>10} {"short":>6} {"mult<>1":>7}')
    allgap = []
    for champ, r in sorted(tot.items(), key=lambda kv: statistics.median(b - a for a, b, m in kv[1])):
        gaps = [b - a for a, b, m in r]
        allgap += gaps
        print(f'{champ:14s} {len(r):5d} {statistics.mean(a for a, b, m in r):6.3f} {statistics.mean(b for a, b, m in r):6.3f} '
              f'{statistics.median(gaps):10.3f} {100.0 * sum(1 for x in gaps if x < -0.02) / len(gaps):5.0f}% '
              f'{100.0 * sum(1 for a, b, m in r if abs(m - 1.0) > 1e-3) / len(r):6.0f}%')
    if allgap:
        print(f'all: {len(allgap)} seconds, median gap {statistics.median(allgap):.3f}, mean {statistics.mean(allgap):.3f}, '
              f'short {100.0 * sum(1 for x in allgap if x < -0.02) / len(allgap):.0f} %')


if __name__ == '__main__':
    main()
