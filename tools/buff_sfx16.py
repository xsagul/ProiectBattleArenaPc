"""The sound events (211) Riot's server plays with a buff, from the replays: when a buff is given (435) or taken away
(262), the 211s of the same frame or the next about its holder or its caster.

211 [m]: +0x40 the event's name ("Play_sfx_Perks_Resolve_BonePlating_OnBuffActivate", "Stop_sfx_..."), +0x60 the
character whose sound bank holds it ("Poppy", "KindredWolf"), +0x70 the unit it plays on, +0x28 a second unit (0 or
a summon), +0x98 a number (16, 10 ...), the other texts empty.

    python tools/buff_sfx16.py [n replays]     -> data/exe1620/buff_sfx16.json
        {buff hash: {'add': [{'name', 'bank': 'holder' | 'caster' | text, 'on': 'holder' | 'caster', 'num', 'delay',
                              'seen'}], 'remove': [...], 'adds': n, 'removes': n}}
A sound is kept when at least half of the buff's adds (removes) had it.
"""
import collections
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'buff_sfx16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def text(x):
    try:
        return bytes.fromhex(x['text']).rstrip(b'\0').decode() if isinstance(x, dict) else ''
    except Exception:
        return ''


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    names = {n: h['champion'] for n, h in R.heroes.items()}
    sfx = collections.defaultdict(list)          # frame -> [(unit, name, bank, num)]
    adds, removes, slot = [], [], {}
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 211)):
        if t > 1200:
            break
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if not v:
            continue
        f = round(t * 30)
        if pid == 211:
            sfx[f].append((u32(v.get('+0x70')), text(v.get('+0x40')), text(v.get('+0x60')), u32(v.get('+0x98'))))
        elif pid == 435:
            slot[(net, v['+0x60'])] = (v['+0x64'], u32(v.get('+0x1c')))
            adds.append((f, net, u32(v.get('+0x1c')), v['+0x64']))
        else:
            h = slot.get((net, v['+0x10']))
            if h:
                removes.append((f, net, h[1], h[0]))
    out = {}

    def look(kind, rows):
        for f0, holder, caster, h in rows:
            b = out.setdefault(h, {'adds': 0, 'removes': 0, 'add': collections.Counter(), 'remove': collections.Counter()})
            b[kind + 's'] += 1
            got = set()
            for d in (0, 1):
                for unit, name, bank, num in sfx.get(f0 + d, ()):
                    on = 'holder' if unit == holder else 'caster' if unit == caster else None
                    if on is None or not name:
                        continue
                    owner = names.get(holder if on == 'holder' else caster)
                    bk = 'unit' if bank == owner else bank
                    k = (name, bk, on, num, d)
                    if (name, on) not in got:
                        got.add((name, on))
                        b[kind][json.dumps(k)] += 1
    look('add', adds)
    look('remove', removes)
    return gid, {h: {'adds': b['adds'], 'removes': b['removes'], 'add': dict(b['add']), 'remove': dict(b['remove'])}
                 for h, b in out.items()}, ''


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, b in part.items():
                t = tot.setdefault(h, {'adds': 0, 'removes': 0, 'add': collections.Counter(), 'remove': collections.Counter()})
                for k in ('adds', 'removes'):
                    t[k] += b[k]
                for k in ('add', 'remove'):
                    t[k].update(b[k])
            print(gid, len(part), err, flush=True)
    res = {}
    for h, t in tot.items():
        r = {'adds': t['adds'], 'removes': t['removes'], 'add': [], 'remove': []}
        for kind in ('add', 'remove'):
            total = t[kind + 's']
            for k, n in t[kind].items():
                if n >= 3 and n >= 0.5 * total:
                    name, bank, on, num, d = json.loads(k)
                    r[kind].append({'name': name, 'bank': bank, 'on': on, 'num': num, 'delay': d, 'seen': n})
        if r['add'] or r['remove']:
            res[h] = r
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs with sounds ->', OUT)


if __name__ == '__main__':
    main()
