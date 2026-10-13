"""The golden test split by champion: for every champion of the batch replays, the packets about it (its own net id)
the replay has, we send and pair, kind by kind - which champions' kits leave the most out.

    python tools/golden_champs16.py [n replays] [--from s] [--to s]   -> data/exe1620/golden16/champs.txt
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import replay_golden16 as G      # noqa: E402


def one(args):
    gid, t0, t1 = args
    try:
        theirs, ours, stats, heroes, champs, logs = G.run(gid, t0, t1)
    except Exception as e:
        return gid, None, repr(e)[:200]
    import replaydb16 as RD
    R = RD.Replay(os.path.join(G.DATA, 'rofl', f'{gid}.rofl'))
    name = {n: h['champion'] for n, h in R.heroes.items() if n in heroes}
    A, B = collections.defaultdict(list), collections.defaultdict(list)
    for side, rows in ((A, theirs), (B, ours)):
        for x in rows:
            if x[2] in heroes:
                side[(name[x[2]], x[1])].append(x[0])
    out = {}
    for key in set(A) | set(B):
        a, b = sorted(A.get(key, [])), sorted(B.get(key, []))
        i = j = m = 0
        while i < len(a) and j < len(b):
            if abs(a[i] - b[j]) <= G.TOL:
                m, i, j = m + 1, i + 1, j + 1
            elif a[i] < b[j]:
                i += 1
            else:
                j += 1
        out[key] = (len(a), len(b), m)
    return gid, out, ''


def main():
    import multiprocessing as mp
    argv = sys.argv[1:]
    n = int(argv[0]) if argv and argv[0].isdigit() else 12
    t0 = float(argv[argv.index('--from') + 1]) if '--from' in argv else 90.0
    t1 = float(argv[argv.index('--to') + 1]) if '--to' in argv else 900.0
    gids = sorted(f[:-5] for f in os.listdir(os.path.join(G.DATA, 'rofl')) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(lambda: [0, 0, 0])
    with mp.Pool(int(os.environ.get('GOLDEN_WORKERS', '4'))) as pool:
        for gid, per, err in pool.imap_unordered(one, [(g, t0, t1) for g in gids]):
            if per is None:
                print(gid, 'failed', err)
                continue
            for k, v in per.items():
                for i in range(3):
                    tot[k][i] += v[i]
    champ = collections.defaultdict(lambda: [0, 0, 0])
    for (c, pid), v in tot.items():
        for i in range(3):
            champ[c][i] += v[i]
    lines = [f'{len(gids)} replays, {t0:.0f} - {t1:.0f} s: packets about each champion (replay / ours / paired), the '
             f'missing ones = replay - paired; the five kinds missing most', '']
    for c, (a, b, m) in sorted(champ.items(), key=lambda x: -(x[1][0] - x[1][2])):
        kinds = sorted(((pid, v) for (cc, pid), v in tot.items() if cc == c), key=lambda x: -(x[1][0] - x[1][2]))[:5]
        lines.append(f'{c:14s} {a - m:6d} missing  ({a} / {b} / {m} = {100.0 * m / max(1, a):5.1f} %)   ' +
                     '  '.join(f'{pid}:{v[0] - v[2]}' for pid, v in kinds))
    open(os.path.join(G.OUT, 'champs.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:40]))


if __name__ == '__main__':
    main()
