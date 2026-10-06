"""Provenance audit of what the test server sends from replay templates: for every field of every template packet,
is it a protocol fact (the same in every comparable case of the replay), an id we swap, a value we compute, or a value
copied from one moment of the replay although it varies there (hardcoded)?

Inputs: data/exe133/templates/<name>.json (what we send), data/exe133/audit_runtime.json (written by
lnp_server.py: the fields it swapped / computed per template packet), data/exe133/codec/<id>.all.jsonl (every
packet of the replay, decoded). Comparable cases = same packet id, same role (the caster's own packets, a target
champion's / unit's, or object 0) and the same key (spell, buff, animation, slot, event name...).

  template_audit.py            -> data/exe133/template_audit.md
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import replay_window as RW  # noqa: E402

CODEC = os.path.join(ROOT, 'data', 'exe133', 'codec')
TPL = os.path.join(ROOT, 'data', 'exe133', 'templates')
RUNTIME = os.path.join(ROOT, 'data', 'exe133', 'audit_runtime.json')
OUT = os.path.join(ROOT, 'data', 'exe133', 'template_audit.md')
HEROES = set(range(0x4000001e, 0x40000028))

# the fields that say WHICH case a packet is (cases are compared only with the same key)
KEYS = {49: [('+0xc', '+0xbc')], 65: [('+0xc',)], 271: [('+0x10',)], 259: [('+0xc', '+0x7')],
        693: [('+0x10',), ('+0x44',)], 522: [('+0x10',)], 326: [('+0x18',)], 220: [('+0x10',)], 721: [('+0xc',)],
        592: [('+0xc', '+0xc')], 750: [('+0x18',)], 215: [('+0x1c',)], 263: [('+0x20',), ('+0xa',)],
        61: [('+0x2c',)], 453: [('+0x10',)]}
D = '1e000040'


def _times(pid, pick, with_obj=False):
    out = sorted((r['t'], r['obj']) for r in (dump(pid) or []) if r['v'] and pick(r))
    return out if with_obj else [t for t, _ in out]


# the moments a template stands for: comparable cases are only taken from those ticks
CONTEXT = {
    'darius_w_cast': lambda: _times(49, lambda r: r['obj'] == 0x4000001e and r['v']['+0xc']['+0xbc'] == '98dd4f05'),
    'darius_w_hit_minion': lambda: _times(522, lambda r: r['obj'] == 0x4000001e and r['v']['+0x10'] == '98dd4f05'),
    'darius_aa': lambda: _times(592, lambda r: r['obj'] == 0x4000001e and r['v']['+0xc']['+0xc'] in ('40', '41')),
    'darius_aa_hit': lambda: _times(263, lambda r: r['v']['+0x20'] == D and r['v']['+0xa'] == '00'),
    'darius_kill_champion': lambda: _times(417, lambda r: 0x4000001e <= r['obj'] <= 0x40000027, True),
    'darius_hemo_refresh': lambda: _times(326, lambda r: r['v']['+0x18'] == D),
    'darius_hemo_tick': lambda: _times(263, lambda r: r['v']['+0x20'] == D and r['v']['+0xa'] == '06'),
}
_dumps = {}


def dump(pid):
    if pid not in _dumps:
        path = os.path.join(CODEC, f'{pid}.all.jsonl')
        _dumps[pid] = [json.loads(line) for line in open(path)] if os.path.exists(path) else None
    return _dumps[pid]


def get(v, path):
    for k in path:
        if not isinstance(v, dict):
            return None
        v = v.get(k)
    return v


def _norm(x):
    """a 4-byte value that reads as a plain float is compared to 4 significant digits (4.0 and 3.999985 are the
    same duration computed with timing noise)"""
    import struct
    if isinstance(x, str) and len(x) == 8:
        f = struct.unpack('<f', bytes.fromhex(x))[0]
        if 1e-3 < abs(f) < 1e5:
            return f'~{f:.4g}'
    return x


def flat(v, path=''):
    if isinstance(v, dict) and 'text' not in v:
        for k, x in v.items():
            yield from flat(x, path + k)
    else:
        yield path, json.dumps(_norm(v), sort_keys=True)


def cases(pid, who, values, caster, target, ctx=None, nth=None):
    """comparable replay cases; nth: the template packet is the nth (1-based) of its id for its object in its tick,
    and only the nth ones of each tick are compared (71: four different lists in a row, each one fixed)"""
    import bisect
    rows = dump(pid)
    if rows is None:
        return None
    keys = KEYS.get(pid, [])
    out = []
    seen = collections.Counter()
    ctx_t, ctx_obj = None, None
    if ctx is not None:
        if ctx and isinstance(ctx[0], tuple):
            ctx_t, ctx_obj = [t for t, _ in ctx], [o for _, o in ctx]
        else:
            ctx_t, ctx_obj = list(ctx), None
    for r in rows:
        seen[(round(r['t'], 3), r['obj'])] += 1
        if nth is not None and seen[(round(r['t'], 3), r['obj'])] != nth:
            continue
        if ctx is not None:
            ts = ctx_t
            i = bisect.bisect_left(ts, r['t'] - 0.002)
            if i >= len(ts) or ts[i] > r['t'] + 0.002:
                continue
            if who == 'target' and ctx_obj is not None and ctx_obj[i] is not None and r['obj'] != ctx_obj[i]:
                continue               # the target role: the unit that has that role in that tick (the victim)
        v, obj = r['v'], r['obj']
        if not v:
            continue
        if who == 'caster' and obj != caster:
            continue
        if who == 'target' and ((target in HEROES) != (obj in HEROES) or obj == 0):
            continue
        if who == 'global' and obj != 0:
            continue
        if any(get(v, k) != get(values, k) for k in keys):
            continue
        out.append(v)
    return out


def main():
    runtime = json.load(open(RUNTIME)) if os.path.exists(RUNTIME) else {}
    lines = ['# Template audit', '', 'Per field: `FIXED` = the same in every comparable replay case (protocol fact); '
             '`id` = swapped by us; `computed` = set by us; **`COPIED`** = copied from one replay moment although it '
             'varies in the replay (hardcoded).', '']
    totals = collections.Counter()
    for name in sorted(f[:-5] for f in os.listdir(TPL) if f.endswith('.json')):
        tpl = json.load(open(os.path.join(TPL, name + '.json')))
        sent = {k: e for k, e in runtime.items() if k.startswith(name + '#')}
        if not sent:
            continue
        lines += [f'## {name} (replay t = {tpl["t"]})', '']
        tpl_ids = {i.to_bytes(4, 'little').hex() for i in (tpl['caster'], tpl['target']) if i}
        for key, e in sorted(sent.items(), key=lambda kv: int(kv[0].split('#')[1])):
            k = int(key.split('#')[1])
            p = tpl['packets'][k]
            ctx = CONTEXT[name]() if name in CONTEXT else None
            nth = sum(1 for q in tpl['packets'][:k + 1] if q['pid'] == p['pid'] and q['who'] == p['who'])
            cs = cases(p['pid'], p['who'], p['values'], tpl['caster'], tpl['target'], ctx, nth)
            if cs is None:
                lines.append(f'- #{k} {p["pid"]} ({p["who"]}): no replay dump')
                continue
            variety = collections.defaultdict(collections.Counter)
            for v in cs:
                for path, x in flat(v):
                    variety[path][x] += 1
            hard, fixed, ids, comp = [], [], [], []
            for path, x in flat(p['values']):
                cov = lambda lst: any(path == c or path.startswith(c) or c.startswith(path) for c in lst)
                if cov(e['computed']):
                    comp.append(path)
                elif cov(e['swapped']) or (isinstance(json.loads(x), str) and json.loads(x).lstrip('~') in tpl_ids):
                    ids.append(path)
                elif len(variety[path]) <= 1:
                    fixed.append(path)
                else:
                    top = variety[path].most_common(3)
                    hard.append(f'{path} ({len(variety[path])} values in {len(cs)} cases, e.g. '
                                f'{", ".join(str(json.loads(t)) if len(t) < 60 else "…" for t, _ in top)})')
            totals['fixed'] += len(fixed)
            totals['id'] += len(ids)
            totals['computed'] += len(comp)
            totals['COPIED'] += len(hard)
            lines.append(f'- #{k} **{p["pid"]}** ({p["who"]}, {len(cs)} replay cases): FIXED {len(fixed)}, id {len(ids)}, '
                         f'computed {len(comp)} {comp if comp else ""}' + (f', **COPIED {len(hard)}**' if hard else ''))
            for h in hard:
                lines.append(f'    - COPIED {h}')
        lines.append('')
    lines.insert(4, f'Totals: {dict(totals)}')
    lines.insert(5, '')
    open(OUT, 'w', encoding='utf8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:6]))
    print('->', OUT)


if __name__ == '__main__':
    main()
