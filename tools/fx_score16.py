"""How well server/core/effects.py's name rules agree with what the real server did with each scripted effect.

    python tools/fx_score16.py [--all]      the live recording's effects (data/live/<match>): rule vs recorded trigger

For every effect the recording's packets 10 create and that is a key of one of the ten champions:
  recorded: 'cast' (same frame as the champion's cast of the effect's slot), 'hit' (same frame as damage the
            champion deals or a buff on the unit it is bound to), 'later' (within 3 s after the cast), 'other'
  rule:     effects.classify(name)
"""
import bisect
import collections
import os
import pickle
import sys

os.environ.setdefault('BA_PATCH', '1620')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import livedb  # noqa: E402
from core import effects  # noqa: E402

SLOT = {0: 0, 1: 1, 2: 2, 3: 3}


def main():
    L = livedb.Live()
    st = pickle.load(open(os.path.join(HERE, '..', 'data', 'exe1620', 'start16.pkl'), 'rb'))
    champ_of = {h.get('net'): (h.get('champion') or h.get('name')) for h in st['heroes']}
    cats = {c: {e['key']: e for e in effects.catalog(c)} for c in set(champ_of.values())}
    u32 = lambda h: int.from_bytes(bytes.fromhex(h), 'little')
    casts, hits, buffs = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for t, way, ch, pid, net, body in L.s2c((1215, 150, 435)):
        v = L.parse(pid, body)
        if not v:
            continue
        if pid == 1215:
            casts[net].append((t, int(v['+0x18']['+0x60'], 16)))
        elif pid == 150:
            hits[u32(v['+0x1c'])].append((t,))
        else:
            buffs[net].append((t,))

    def near(lst, t, lo, hi):
        i = bisect.bisect_left(lst, (t + lo,))
        return [x for x in lst[i:i + 8] if x[0] <= t + hi]
    seen = collections.defaultdict(collections.Counter)
    for t, way, ch, pid, net, body in L.s2c(10):
        v = L.parse(10, body)
        if not v:
            continue
        for g in v['+0x10']:
            key = u32(g['+0x20'])
            for inst in g['+0x10']:
                caster, bound = u32(inst['+0x18']), u32(inst['+0x34'])
                c = champ_of.get(caster)
                if c is None or key not in cats[c]:
                    continue
                name = cats[c][key]['name']
                slot, rule, lasts = effects.classify(c, name)
                same = [x for x in near(casts[caster], t, -0.04, 0.04) if slot is None or x[1] == slot or x[1] > 3]
                if same:
                    what = 'cast'
                elif near(hits[caster], t, -0.04, 0.04) or (bound and bound != caster and near(buffs[bound], t, -0.04, 0.04)):
                    what = 'hit'
                elif near(buffs[bound], t, -0.04, 0.04):
                    what = 'buff'
                elif near(casts[caster], t, -3.0, -0.04):
                    what = 'later'
                else:
                    what = 'other'
                seen[(c, name)][what] += 1
    agree = collections.Counter()
    rows = []
    for (c, name), cnt in seen.items():
        e = next(x for x in effects.catalog(c) if x['name'] == name)
        slot, rule, lasts = effects.classify(c, name)
        top = cnt.most_common(1)[0][0]
        n = sum(cnt.values())
        if e['data']:
            verdict = 'data'
        elif rule is None:
            verdict = 'not shown'
        elif (rule == 'cast' and top == 'cast') or (rule in ('hit', 'held') and top in ('hit', 'buff', 'later')) or \
                (rule == 'place' and top in ('cast', 'later')):
            verdict = 'agrees'
        else:
            verdict = 'differs'
        agree[verdict] += n
        agree['effects ' + verdict] += 1
        rows.append((verdict, -n, c, name, rule, dict(cnt)))
    total = sum(v for k, v in agree.items() if not k.startswith('effects'))
    print('effects shown by the recording:', len(rows), '| instances', total)
    for k in ('agrees', 'differs', 'not shown', 'data'):
        print(f'  {k:10s} {agree[k]:6d} instances ({100.0 * agree[k] / max(1, total):.1f} %), {agree["effects " + k]} effects')
    if '--all' in sys.argv:
        for verdict, n, c, name, rule, cnt in sorted(rows):
            print(f'  {verdict:10s} {name:46s} rule {str(rule):6s} recorded {cnt}')
    else:
        for want in ('differs', 'not shown'):
            for verdict, n, c, name, rule, cnt in sorted(rows):
                if verdict == want and -n >= 12:
                    print(f'  {verdict:10s} {name:46s} rule {str(rule):6s} recorded {cnt}')


if __name__ == '__main__':
    main()
