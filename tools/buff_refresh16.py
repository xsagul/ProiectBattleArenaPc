"""Buffs that Riot's server renews on every script update while they last (282 NPC_BuffUpdateCount every 0.267 s: an area's
slow / poison / haste on the units standing in it, an aura, "in combat"), from the replays.

    python tools/buff_refresh16.py [n replays]     -> data/exe1620/buff_refresh16.json
        {buff name hash (hex): {'dur': the duration each 282 sets, 'count': its count, 'share': part of the buff's life
         covered by 282s one update apart, 'n': 282s seen, 'first': median s from the 435 to the first 282,
         'period': frames between two 282s (8 = a script update, 1 = every frame, 2 ...)}}
Buffs still on when the recording ends count until its end (a passive's lasting buff: Kindred's 2641d004).

282 [m]: +0x10 the duration set (f32), +0x14 0, +0x18 the buff's slot, +0x1c the caster, +0x20 the count. The server
(core/spells.py buff_refresher) sends them on the buff holder's script clock while the buff is on.
"""
import collections
import json
import multiprocessing as mp
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'buff_refresh16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    live = {}                 # (net, slot) -> [hash, t0, [282 times], [(dur, count)]]
    done = collections.defaultdict(list)
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 282)):
        if t > 1200:
            break
        if t != frame:
            frame, seen = t, set()
        v = R.parse(pid, body)
        if not v:
            continue
        sig = (pid, net, json.dumps(v, sort_keys=True))
        if sig in seen:
            continue
        seen.add(sig)
        if pid == 435:
            k = (net, v['+0x60'])
            if k in live:
                done[live[k][0]].append(live.pop(k) + [t])
            live[k] = [v['+0x64'], t, [], []]
        elif pid == 262:
            k = (net, v['+0x10'])
            if k in live:
                done[live[k][0]].append(live.pop(k) + [t])
        else:
            k = (net, v['+0x18'])
            if k in live:
                live[k][2].append(t)
                live[k][3].append((round(struct.unpack('<f', bytes.fromhex(v['+0x10']))[0], 3), int(v['+0x20'], 16)))
    for k, x in live.items():
        done[x[0]].append(x + [min(t, 1200.0)])
    out = {}
    for h, lives in done.items():
        r = out.setdefault(h, {'life': 0.0, 'covered': 0.0, 'vals': collections.Counter(), 'first': [], 'n': 0,
                               'gaps': collections.Counter()})
        for hh, t0, ts, vals, t1 in lives:
            r['life'] += max(0.0, t1 - t0)
            r['n'] += len(ts)
            r['vals'].update(vals)
            if ts:
                r['first'].append(ts[0] - t0)
            for a, b in zip(ts, ts[1:]):
                if b - a < 0.35:
                    r['covered'] += b - a
                    r['gaps'][max(1, round((b - a) * 30))] += 1
    return gid, {h: dict(r, vals=dict(r['vals']), gaps=dict(r['gaps'])) for h, r in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, r in part.items():
                t = tot.setdefault(h, {'life': 0.0, 'covered': 0.0, 'vals': collections.Counter(), 'first': [], 'n': 0,
                                       'gaps': collections.Counter()})
                t['gaps'].update(r['gaps'])
                t['life'] += r['life']
                t['covered'] += r['covered']
                t['n'] += r['n']
                t['vals'].update(r['vals'])
                t['first'].extend(r['first'])
            print(gid, len(part), err, flush=True)
    res = {}
    for h, t in tot.items():
        if t['n'] < 20 or t['life'] <= 0:
            continue
        share = t['covered'] / t['life']
        if share < 0.5:
            continue
        (dur, count), _ = t['vals'].most_common(1)[0]
        res[h] = {'dur': dur, 'count': count, 'share': round(share, 2), 'n': t['n'],
                  'first': round(statistics.median(t['first']), 3) if t['first'] else None,
                  'period': t['gaps'].most_common(1)[0][0] if t['gaps'] else 8}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs renewed on every update ->', OUT)


if __name__ == '__main__':
    main()
