"""The effects Riot's server makes together with a buff, from the replays: for every buff given (435), the packet-10
effects of the buff's caster made in the same frame or the next, bound to the buff's unit, to the caster or to a place;
and whether the effect is taken away (584) in the frame the buff ends (262).

[m: 3 replays, 90 - 900 s] 16,000 of 42,000 effects are born with a buff; of the 8,515 of them a 584 ends, 6,724 end in
the frame their buff does (Lillia's poison, Fiora's passive speed, Anivia's chill ...).

    python tools/buff_fx16.py [n replays]      -> data/exe1620/buff_fx16.json

{buff hash: {'adds': n, 'fx': [{'key' (hex, or 'old:<+0x8>'), 'seen': adds with it, 'bound': 'target' | 'caster' |
 'place', 'delay': frames after the 435, 'with_buff': share ended in the buff's end frame, 'lasts': median s to its 584
 when most others end by one (else None: it ends by itself), 'target', 'bone', 'target_bone', 'flags', 'tag',
 'scale', 'keyword'}]}}
An effect is kept when at least half of the buff's adds had it (server/core/effects.py on_buff_add / on_buff_remove).
"""
import collections
import json
import multiprocessing as mp
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
OUT = os.path.join(ROOT, 'data', 'exe1620', 'buff_fx16.json')
DATA = os.path.join(ROOT, 'data', 'replays16', 'rofl')
T1 = 1200.0


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0


def scan(gid):
    import replaydb16
    try:
        R = replaydb16.Replay(os.path.join(DATA, f'{gid}.rofl'))
    except Exception as x:
        return gid, {}, repr(x)
    adds = []                                    # (frame, target, caster, slot, hash)
    fx_by = collections.defaultdict(list)        # (frame, caster) -> [(key, inst, group)]
    ends = {}                                    # (target, slot) -> [end frames]
    fx_end = {}
    slot_hash = {}
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=(435, 262, 10, 584)):
        if t > T1:
            break
        if t != frame:
            frame, seen = t, set()
        if (pid, net, body) in seen:
            continue
        seen.add((pid, net, body))
        v = R.parse(pid, body)
        if v is None:
            continue
        f = round(t * 30)
        if pid == 435:
            adds.append((f, net, u32(v.get('+0x1c')), v.get('+0x60'), v.get('+0x64')))
            slot_hash[(net, v.get('+0x60'))] = v.get('+0x64')
            ends.setdefault((net, v.get('+0x60')), []).append(('add', f))
        elif pid == 262:
            ends.setdefault((net, v.get('+0x10')), []).append(('end', f))
        elif pid == 10:
            for g in v.get('+0x10') or []:
                if not isinstance(g, dict):
                    continue
                key = g.get('+0x20') if g.get('+0x20') not in (None, '00000000') else 'old:' + str(g.get('+0x8'))
                for i in g.get('+0x10') or []:
                    if isinstance(i, dict):
                        fx_by[(f, u32(i.get('+0x18')))].append((key, i, g))
        else:
            fx_end.setdefault(u32(v.get('+0x14')), f)

    def buff_end(target, slot, f0):
        for kind, f in ends.get((target, slot), ()):
            if f > f0 and kind in ('end', 'add'):
                return f if kind == 'end' else f      # given again in the slot: the old one ended then
        return None
    out = {}
    for f0, target, caster, slot, h in adds:
        b = out.setdefault(h, {'adds': 0, 'fx': {}})
        b['adds'] += 1
        fe = buff_end(target, slot, f0)
        got = set()
        for df in (0, 1):
            for key, inst, g in fx_by.get((f0 + df, caster), ()):
                bound = u32(inst.get('+0x34'))
                role = 'target' if bound == target else 'caster' if bound == caster else 'place' if not bound else None
                if role is None or (key, role) in got:
                    continue
                got.add((key, role))
                eid = u32(inst.get('+0x38'))
                e = fx_end.get(eid)
                k = b['fx'].setdefault(f'{key}|{role}', {'seen': 0, 'rec': []})
                k['seen'] += 1
                if len(k['rec']) < 300:
                    k['rec'].append({'delay': df, 'with_buff': e is not None and fe is not None and abs(e - fe) <= 1,
                                     'lasts': (e - f0 - df) / 30.0 if e is not None else None,
                                     'target': u32(inst.get('+0xb8')) == target and target != 0,
                                     'bone': g.get('+0xc'), 'target_bone': g.get('+0x38'), 'flags': g.get('+0x50'),
                                     'tag': (g.get('+0x28') or [None])[0], 'scale': inst.get('+0x14'),
                                     'keyword': u32(inst.get('+0x3c')) == caster and caster != 0})
    return gid, out, ''


def most(xs):
    xs = [x for x in xs if x is not None]
    return collections.Counter(xs).most_common(1)[0][0] if xs else None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    gids = sorted(f[:-5] for f in os.listdir(DATA) if f.endswith('.rofl'))[:n]
    tot = {}
    with mp.Pool(4) as pool:
        for gid, part, err in pool.imap_unordered(scan, gids):
            for h, b in part.items():
                t = tot.setdefault(h, {'adds': 0, 'fx': {}})
                t['adds'] += b['adds']
                for k, x in b['fx'].items():
                    tk = t['fx'].setdefault(k, {'seen': 0, 'rec': []})
                    tk['seen'] += x['seen']
                    tk['rec'].extend(x['rec'][:300])
            print(gid, len(part), err, flush=True)
    res = {}
    for h, t in tot.items():
        fxs = []
        for k, x in t['fx'].items():
            if x['seen'] < 3 or x['seen'] < 0.5 * t['adds']:
                continue
            key, role = k.split('|')
            rs = x['rec']
            ended = [r for r in rs if r['lasts'] is not None]
            withb = sum(1 for r in rs if r['with_buff'])
            fxs.append({'key': key, 'bound': role, 'seen': x['seen'], 'delay': most(r['delay'] for r in rs),
                        'with_buff': round(withb / max(1, len(rs)), 2),
                        'lasts': round(statistics.median(r['lasts'] for r in ended), 3)
                        if len(ended) * 2 >= len(rs) and withb * 2 < len(rs) else None,
                        'target': most(r['target'] for r in rs), 'bone': most(r['bone'] for r in rs),
                        'target_bone': most(r['target_bone'] for r in rs), 'flags': most(r['flags'] for r in rs),
                        'tag': most(r['tag'] for r in rs), 'scale': most(r['scale'] for r in rs),
                        'keyword': most(r['keyword'] for r in rs)})
        if fxs:
            res[h] = {'adds': t['adds'], 'fx': sorted(fxs, key=lambda e: -e['seen'])}
    json.dump(res, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(res), 'buffs with effects ->', OUT)
    try:
        import elf_names16
        top = sorted(res.items(), key=lambda kv: -kv[1]['adds'])[:15]
        for h, r in top:
            print(f"  {elf_names16.name(h) or h}: {r['adds']} adds, " +
                  ', '.join(f"{e['key']} {e['bound']} {e['seen']} with_buff {e['with_buff']} lasts {e['lasts']}" for e in r['fx'][:3]))
    except Exception:
        pass


if __name__ == '__main__':
    main()
