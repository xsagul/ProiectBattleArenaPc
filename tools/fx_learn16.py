"""What the real server did with each scripted effect of the recorded champions -> data/exe1620/gamedata/fx_live.json

    python tools/fx_learn16.py            learn from data/live/<match> and write the table; prints what was learnt

For every packet-10 instance whose caster is one of the ten champions and whose key is in that champion's
resource map (server/core/effects.catalog):
    when     'cast' = the frame of the champion's cast (which slot), 'hit' = the frame of damage it deals / of a buff
             on the unit the effect is bound to (bound to another unit), 'after' = up to 3 s after its cast of the
             effect's slot (the delay is kept), else not learnt
    where    bound to the caster, to another unit, or to no unit (a place; at the caster or away from it)
    how      the group's bone and target bone (ELF hashes), flags, tag; the instance's scale; whether it carries
             the caster as keyword / target / owner place
    how long the time until a 584 names the effect's net id (None = it ends by itself)
The table per champion: {key: {name, slot, when, delay, where, bone, target_bone, flags, tag, scale, keyword,
target, owner_place, lasts, seen}} with the most frequent choice of each.
"""
import bisect
import collections
import json
import os
import pickle
import statistics
import struct
import sys

os.environ.setdefault('BA_PATCH', '1620')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import livedb  # noqa: E402
from core import effects, gamedata as G  # noqa: E402

OUT = os.path.join(G.OUT, 'fx_live.json')


def main():
    L = livedb.Live()
    st = pickle.load(open(os.path.join(HERE, '..', 'data', 'exe1620', 'start16.pkl'), 'rb'))
    champ_of = {h.get('net'): (h.get('champion') or h.get('name')) for h in st['heroes']}
    cats = {c: {e['key']: e for e in effects.catalog(c)} for c in set(champ_of.values())}
    u32 = lambda h: int.from_bytes(bytes.fromhex(h), 'little')
    i16 = lambda h: struct.unpack('<h', bytes.fromhex(h))[0]
    casts, hits, buffs = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    made, ended = {}, {}
    rows = []
    for t, way, ch, pid, net, body in L.s2c((1215, 150, 435, 584, 10)):
        v = L.parse(pid, body)
        if not v:
            continue
        if pid == 1215:
            casts[net].append((t, int(v['+0x18']['+0x60'], 16)))
        elif pid == 150:
            hits[u32(v['+0x1c'])].append((t,))
        elif pid == 435:
            buffs[net].append((t,))
        elif pid == 584:
            fx = u32(v['+0x14'])
            if fx in made and fx not in ended:
                ended[fx] = t - made[fx]
        else:
            for g in v['+0x10']:
                key = u32(g['+0x20'])
                for inst in g['+0x10']:
                    caster = u32(inst['+0x18'])
                    c = champ_of.get(caster)
                    if c is None or key not in cats[c]:
                        continue
                    fx = u32(inst['+0x38'])
                    made[fx] = t
                    rows.append((t, c, caster, key, g, inst, fx))

    def near(lst, t, lo, hi):
        i = bisect.bisect_left(lst, (t + lo,))
        return [x for x in lst[i:i + 8] if x[0] <= t + hi]
    votes = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    delays = collections.defaultdict(list)
    lives = collections.defaultdict(list)
    for t, c, caster, key, g, inst, fx in rows:
        name = cats[c][key]['name']
        slot, rule, _ = effects.classify(c, name)
        bound = u32(inst['+0x34'])
        same = near(casts[caster], t, -0.04, 0.04)
        named = [x for x in same if x[1] == slot]
        when, cast_slot, delay = None, slot, 0.0
        if same:
            when, cast_slot = 'cast', (named or same)[-1][1]
        elif bound and bound != caster and (near(hits[caster], t, -0.04, 0.04) or near(buffs[bound], t, -0.04, 0.04)):
            when = 'hit'
        else:
            before = [x for x in near(casts[caster], t, -3.0, -0.04) if slot is None or isinstance(slot, str) or x[1] == slot]
            if before:
                when, cast_slot, delay = ('hit' if bound and bound != caster else 'after'), before[-1][1], t - before[-1][0]
        if when is None or not isinstance(cast_slot, int) or cast_slot > 3:
            when = None
        k = (c, key)
        v = votes[k]
        v['when'][(when, cast_slot if when else None)] += 1
        if when is None:
            continue
        if when == 'after':
            delays[k].append(delay)
        own = (i16(inst['+0xe']), i16(inst['+0x10']))
        here = (i16(inst['+0xac']), i16(inst['+0x20']))
        where = 'self' if bound == caster else 'unit' if bound else ('place' if own == effects.NO_PLACE or abs(own[0] - here[0]) + abs(own[1] - here[1]) > 40 else 'self place')
        v['where'][where] += 1
        v['bone'][u32(g['+0xc'])] += 1
        v['target_bone'][u32(g['+0x38'])] += 1
        v['flags'][struct.unpack('<H', bytes.fromhex(g['+0x50']))[0]] += 1
        v['tag'][u32(g['+0x28'][0]) if g['+0x28'] else 0] += 1
        v['scale'][round(struct.unpack('<f', bytes.fromhex(inst['+0x14']))[0], 3)] += 1
        v['keyword'][u32(inst['+0x3c']) == caster] += 1
        v['target'][u32(inst['+0xb8']) == caster] += 1
        v['owner_place'][own != effects.NO_PLACE] += 1
        lives[k].append(ended.get(fx))
    out = collections.defaultdict(dict)
    stats = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for (c, key), v in votes.items():
        (when, slot), n = v['when'].most_common(1)[0]
        total = sum(v['when'].values())
        if when is None or n < 2 or n < 0.4 * total:
            continue
        top = lambda f: v[f].most_common(1)[0][0]
        ends = [x for x in lives[(c, key)] if x is not None]
        e = {'name': cats[c][key]['name'], 'slot': slot, 'when': when,
             'delay': round(statistics.median(delays[(c, key)]), 2) if when == 'after' and delays[(c, key)] else 0.0,
             'where': top('where'), 'bone': top('bone'), 'target_bone': top('target_bone'), 'flags': top('flags'),
             'tag': top('tag'), 'scale': top('scale'), 'keyword': top('keyword'), 'target': top('target'),
             'owner_place': top('owner_place'),
             'lasts': round(statistics.median(ends), 2) if len(ends) >= 0.5 * len(lives[(c, key)]) and ends else None,
             'seen': total}
        out[c][f'{key:08x}'] = e
        for f in ('bone', 'target_bone', 'flags', 'tag', 'keyword', 'target', 'owner_place'):
            stats[(when, e['where'])][f][e[f]] += 1
    json.dump(out, open(OUT, 'w'), indent=1)
    n = sum(len(v) for v in out.values())
    print(f'{n} effects of {len(out)} champions learnt -> {os.path.relpath(OUT)}')
    for c in sorted(out):
        by = collections.Counter((e['when'], e['where']) for e in out[c].values())
        print(f'  {c:12s} {len(out[c]):3d}  {dict(by)}')
    print('how the real server sends them, by when / where (effects):')
    for k in sorted(stats, key=str):
        print(' ', k, {f: [(hex(x) if isinstance(x, int) and not isinstance(x, bool) else x, n) for x, n in c.most_common(3)] for f, c in stats[k].items()})


if __name__ == '__main__':
    main()
