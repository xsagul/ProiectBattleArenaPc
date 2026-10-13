"""Buffs a champion holds by a CONDITION (a passive, an item, a rune: "in combat", "unseen", "always"), from the replays:
the buffs a champion gets not by a cast and that the server renews on its script updates (282), set against states our
server knows too, sampled every 0.267 s:
  always       the buff is there whenever the champion lives
  unseen       the enemy team does not see the champion (723 / 1195 of the other team)
  combat_hero  it dealt or took champion damage in the last 3 s        combat_any  any damage in the last 3 s
The condition kept is the one with the buff present >= 85 % of the time it holds and <= 15 % of the time it does not.
Owner: the champion when one champion has it; else the item every holder had (63 purchases).

    python tools/self_buffs16.py [n replays]     -> data/exe1620/self_buffs16.json
        {buff hash: {'cond', 'type', 'dur', 'count', 'owner': champion | 'item:<id>', 'p': [p_on, p_off], 'n'}}
"""
import bisect
import collections
import json
import multiprocessing as mp
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'data', 'exe1620', 'self_buffs16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
STEP = 0.26729
CONDS = ('always', 'unseen', 'combat_hero', 'combat_any', 'combat_hero5', 'combat_any5', 'active5')


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    import replay_golden16 as RG
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    H = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    nets = sorted(H)[:10]
    team = {n: ('01' if i < 5 else '02') for i, n in enumerate(nets)}
    T1 = 900.0
    sight = RG.team_sight(R, T1)
    slots, bufflife = {}, collections.defaultdict(list)       # (hero, hash) -> [(t0, t1)]
    casts, dmg_hero, dmg_any, deaths, items, meta = collections.defaultdict(list), collections.defaultdict(list), \
        collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(set), {}
    renewed = collections.Counter()
    frame, seen = None, set()
    moves = collections.defaultdict(list)
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 282, 1215, 150, 1112, 63, 421, 61)):
        if t > T1:
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
        if pid == 61:
            try:
                import waypoints
                for e in waypoints.parse(bytes.fromhex(v['+0x18']['text'])):
                    if e['net'] in H:
                        moves[e['net']].append(t)
            except Exception:
                pass
            continue
        if pid == 1215 and net in H:
            casts[net].append(t)
        elif pid == 63 and net in H:
            items[net].add(u32(v['+0x18']['+0x18']))
        elif pid in (1112, 421) and net in H:
            deaths[net].append(t)              # [10-13] a champion's death is 421 (NPC_Hero_Die), not 1112
        elif pid == 150:
            src = u32(v.get('+0x1c'))
            for a, b in ((src, net), (net, src)):
                if a in H:
                    dmg_any[a].append(t)
                    if b in H:
                        dmg_hero[a].append(t)
        elif pid == 435 and net in H:
            cs = casts.get(net, [])
            i = bisect.bisect_right(cs, t) - 1
            by_cast = i >= 0 and t - cs[i] < 0.3
            k = (net, v['+0x60'])
            old = slots.pop(k, None)
            if old:
                bufflife[(net, old[0])].append((old[1], t))
            if not by_cast and u32(v.get('+0x1c')) == net:
                slots[k] = (v['+0x64'], t)
                meta.setdefault(v['+0x64'], (v['+0x38'], round(struct.unpack('<f', bytes.fromhex(v['+0x3c']))[0], 2)))
        elif pid == 262 and net in H:
            old = slots.pop((net, v['+0x10']), None)
            if old:
                bufflife[(net, old[0])].append((old[1], t))
        elif pid == 282 and net in H:
            old = slots.get((net, v['+0x18']))
            if old:
                renewed[old[0]] += 1
    for (net, slot), (h, t0) in slots.items():
        bufflife[(net, h)].append((t0, T1))
    out = {}
    for (net, h), lives in bufflife.items():
        if renewed[h] < 5:
            continue
        r = out.setdefault(h, {'counts': {c: [0, 0, 0, 0] for c in CONDS}, 'champs': collections.Counter(), 'items': None,
                               'meta': meta.get(h)})
        r['champs'][H[net]] += 1
        r['items'] = items[net] if r['items'] is None else (r['items'] & items[net])
        da, dh, dd = sorted(dmg_any[net]), sorted(dmg_hero[net]), sorted(deaths[net])
        mv = sorted(moves[net])
        act = sorted(da + casts.get(net, []))            # damage dealt / taken or a cast
        # dead from the death until its first walk after it (the respawn), at most 80 s
        dead = []
        for d0 in dd:
            j = bisect.bisect_right(mv, d0 + 1.0)
            dead.append((d0, min(d0 + 80.0, mv[j] if j < len(mv) else d0 + 80.0)))
        first = min(a for a, b in lives)
        t = max(90.0, first - 30.0)
        while t < T1 - 1:
            on = any(a <= t <= b for a, b in lives)
            if any(a - 0.5 <= t <= b + 0.5 for a, b in dead):    # dead: skip
                t += STEP
                continue
            vis = any(a <= t <= b for a, b in sight['01' if team[net] == '02' else '02'].get(net, ()))
            state = {'always': True, 'unseen': not vis,
                     'combat_hero': bool(dh) and (lambda j: j >= 0 and t - dh[j] < 3.0)(bisect.bisect_right(dh, t) - 1),
                     'combat_any': bool(da) and (lambda j: j >= 0 and t - da[j] < 3.0)(bisect.bisect_right(da, t) - 1),
                     'combat_hero5': bool(dh) and (lambda j: j >= 0 and t - dh[j] < 5.0)(bisect.bisect_right(dh, t) - 1),
                     'combat_any5': bool(da) and (lambda j: j >= 0 and t - da[j] < 5.0)(bisect.bisect_right(da, t) - 1),
                     'active5': bool(act) and (lambda j: j >= 0 and t - act[j] < 5.0)(bisect.bisect_right(act, t) - 1)}
            for c in CONDS:
                x = r['counts'][c]
                if state[c]:
                    x[0] += 1
                    x[1] += on
                else:
                    x[2] += 1
                    x[3] += on
            t += STEP
    return gid, {h: dict(r, champs=dict(r['champs']), items=sorted(r['items'] or ())) for h, r in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(int(os.environ.get('WORKERS', '4'))) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, r in part.items():
                t = tot.setdefault(h, {'counts': {c: [0, 0, 0, 0] for c in CONDS}, 'champs': collections.Counter(), 'items': None,
                                       'meta': r['meta']})
                for c in CONDS:
                    t['counts'][c] = [a + b for a, b in zip(t['counts'][c], r['counts'][c])]
                t['champs'].update(r['champs'])
                its = set(r['items'])
                t['items'] = its if t['items'] is None else (t['items'] & its)
            print(gid, len(part), err, flush=True)
    import elf_names16
    res = {}
    for h, t in tot.items():
        best = None
        for c in CONDS:
            on_n, on_b, off_n, off_b = t['counts'][c]
            if on_n < 50:
                continue
            p_on = on_b / on_n
            p_off = off_b / off_n if off_n else 0.0
            if p_on >= 0.85 and p_off <= 0.15 and (best is None or p_on - p_off > best[1]):
                best = (c, p_on - p_off, p_on, p_off, on_n)
        if not best or not t['meta']:
            continue
        top, top_n = max(t['champs'].items(), key=lambda kv: kv[1])
        owner = top if top_n >= 0.9 * sum(t['champs'].values()) else \
            ('item:%d' % sorted(i for i in t['items'] if 1000 <= i < 9000)[0]) if any(1000 <= i < 9000 for i in (t['items'] or ())) else 'any'
        res[h] = {'cond': best[0], 'type': int(t['meta'][0], 16), 'dur': t['meta'][1], 'owner': owner,
                  'p': [round(best[2], 2), round(best[3], 2)], 'n': best[4], 'name': elf_names16.name(h)}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs held by a condition ->', OUT)
    for h, r in sorted(res.items(), key=lambda kv: -kv[1]['n'])[:20]:
        print(h, r)


if __name__ == '__main__':
    main()
