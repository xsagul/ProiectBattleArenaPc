"""Automatic per-spell templates for every champion of the replay: what Riot's server sends at each of its casts.

For every (champion, spell) cast at least 3 times in the replay:
- the caster's packets in the cast's tick (49 and what comes with it), decoded; the most common sequence of packet
  ids is the template (its first case), and every field is classed over all the casts with that sequence: FIXED (the
  same every time = protocol fact, copied) or varying (must be computed: times, ids, positions, ranks...);
- what the cast does to others in the following second: buffs put by the caster (693 with +0x44 = the caster: name,
  type, duration), damage by the caster (263 with +0x20 = the caster: delay after the cast, damage type).

Output: research/exe133/templates/auto/<Champion>/<Spell>.json and an index research/exe133/templates/auto/index.json.

  auto_templates.py [Champion ...]
"""
import bisect
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import replay_window as RW  # noqa: E402
import name_hashes as N  # noqa: E402

OUT = os.path.join(ROOT, 'research', 'exe133', 'templates', 'auto')
CODEC = os.path.join(ROOT, 'research', 'exe133', 'codec')


def hero_names():
    rows = json.load(open(os.path.join(ROOT, 'research', 'exe133', 's2c_79_heroes.json'), encoding='utf8'))
    return {r['net_id']: r['champion'] for r in rows}


def name_of(h):
    x = N.find(int.from_bytes(bytes.fromhex(h), 'little'))
    return x[0][1] if x else h


def flat(v, path=''):
    if isinstance(v, dict) and 'text' not in v:
        for k, x in v.items():
            yield from flat(x, path + k)
    else:
        yield path, json.dumps(v, sort_keys=True)


def main(only=None):
    heroes = hero_names()
    casts = collections.defaultdict(list)          # (net, spell hash) -> [t]
    for line in open(os.path.join(CODEC, '49.all.jsonl')):
        r = json.loads(line)
        if r['v'] and r['obj'] in heroes:
            casts[(r['obj'], r['v']['+0xc']['+0xbc'])].append(r['t'])
    # every packet of the heroes (bodies) and the damage / buffs they cause, in one pass over the replay
    P.KINDS, P.ENTRY = (1,), None
    by_tick = collections.defaultdict(list)        # (round t, net) -> [(pid, body)]
    for t, ch, pid, obj, body in P.packets(P.ROFL):
        if obj in heroes and pid not in RW.NOISE:
            by_tick[(round(t, 3), obj)].append((t, ch, pid, body))
    dmg = collections.defaultdict(list)            # source net -> [(t, target, type)]
    for line in open(os.path.join(CODEC, '263.all.jsonl')):
        r = json.loads(line)
        if r['v']:
            src = int.from_bytes(bytes.fromhex(r['v']['+0x20']), 'little')
            if src in heroes:
                dmg[src].append((r['t'], r['obj'], int(r['v']['+0x10'], 16)))
    buffs = collections.defaultdict(list)          # source net -> [(t, target, name, type, duration)]
    for line in open(os.path.join(CODEC, '693.all.jsonl')):
        r = json.loads(line)
        v = r['v']
        if v:
            src = int.from_bytes(bytes.fromhex(v['+0x44']), 'little')
            if src in heroes:
                buffs[src].append((r['t'], r['obj'], name_of(v['+0x10']), int(v['+0x34'], 16),
                                   round(struct.unpack('<f', bytes.fromhex(v['+0x18']))[0], 3)))
    index = {}
    casts_by_name = {(net, name_of(sh)): ts for (net, sh), ts in casts.items()}
    for (net, sh), ts in sorted(casts.items()):
        champ = heroes[net]
        if only and champ not in only:
            continue
        spell = name_of(sh)
        if len(ts) < 3:
            continue
        seqs = collections.Counter()
        tick_of = {}
        for t in ts:
            seq = tuple(pid for _, _, pid, _ in sorted(by_tick.get((round(t, 3), net), []), key=lambda x: x[0]))
            seqs[seq] += 1
            tick_of.setdefault(seq, []).append(t)
        seq, n = seqs.most_common(1)[0]
        cases = tick_of[seq]
        # decode every case of the modal sequence, position by position
        variety = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
        first = None
        for t in cases[:40]:
            pk = sorted(by_tick[(round(t, 3), net)], key=lambda x: x[0])
            decoded = []
            for k, (tt, ch, pid, body) in enumerate(pk):
                v = RW.decode(pid, net, body)
                decoded.append({'pid': pid, 'ch': ch, 'who': 'caster', 'values': v, 'raw': None if v is not None else body.hex()})
                if v is not None:
                    for path, x in flat(v):
                        variety[k][path][x] += 1
            if first is None:
                first = (t, decoded)
        fixed = {k: sorted(p for p, c in d.items() if len(c) == 1) for k, d in variety.items()}
        varying = {k: sorted(p for p, c in d.items() if len(c) > 1) for k, d in variety.items()}
        # effects on others within a second: damage and buffs by this caster
        dd = dmg[net]
        dt_ = [x[0] for x in dd]
        delays, kinds = collections.Counter(), collections.Counter()
        for t in ts:
            i = bisect.bisect_left(dt_, t)
            while i < len(dd) and dd[i][0] <= t + 1.0:
                if dd[i][1] != net:
                    delays[round(dd[i][0] - t, 2)] += 1
                    kinds[dd[i][2]] += 1
                i += 1
        bb = buffs[net]
        bt_ = [x[0] for x in bb]
        applies = collections.Counter()
        for t in ts:
            i = bisect.bisect_left(bt_, t - 0.002)
            while i < len(bb) and bb[i][0] <= t + 1.0:
                tgt = 'self' if bb[i][1] == net else 'other'
                applies[(tgt, bb[i][2], bb[i][3], bb[i][4])] += 1
                i += 1
        out = {'champion': champ, 'spell': spell, 'caster': net, 'target': None, 't': first[0], 'casts': len(ts),
               'sequence': list(seq), 'sequence_cases': n, 'sequences': len(seqs),
               'packets': first[1], 'fixed': fixed, 'varying': varying,
               'damage_delays': delays.most_common(8), 'damage_types': dict(kinds),
               'applies': [list(k) + [c] for k, c in applies.most_common(12)]}
        os.makedirs(os.path.join(OUT, champ), exist_ok=True)
        json.dump(out, open(os.path.join(OUT, champ, f'{spell}.json'), 'w'), indent=1)
        index.setdefault(champ, {})[spell] = {'casts': len(ts), 'sequence': list(seq), 'modal_share': round(n / len(ts), 2),
                                              'damage_types': dict(kinds), 'applies': len(applies)}
        print(f'{champ:10s} {spell[:32]:32s} {len(ts):4d} casts, sequence {list(seq)} in {n}, '
              f'damage {dict(kinds)}, buffs {[(a[1][:24], a[3]) for a in applies][:3]}', flush=True)
    # attacks: the caster's 592 (+ 516) tick, per attack slot and attack spell (0x40 / 0x41 basic, 0x2d... special)
    att = collections.defaultdict(list)
    for line in open(os.path.join(CODEC, '592.all.jsonl')):
        r = json.loads(line)
        if r['v'] and r['obj'] in heroes:
            a = r['v']['+0xc']
            inner = name_of(a['+0x10'][0]['+0xbc']) if a['+0x10'] else ''
            att[(r['obj'], a['+0xc'], inner)].append(r['t'])
    for (net, slot, inner), ts in sorted(att.items()):
        champ = heroes[net]
        if (only and champ not in only) or len(ts) < 3:
            continue
        t = ts[0]
        pk = [x for x in sorted(by_tick[(round(t, 3), net)], key=lambda x: x[0]) if x[2] in (592, 516)]
        decoded = []
        for tt, ch, pid, body in pk:
            decoded.append({'pid': pid, 'ch': ch, 'who': 'caster', 'values': RW.decode(pid, net, body), 'raw': None})
        name = f'attack_{slot}' + (f'_{inner}' if inner else '')
        out = {'champion': champ, 'spell': name, 'caster': net, 'target': None, 't': t, 'casts': len(ts),
               'sequence': [d['pid'] for d in decoded], 'packets': decoded, 'fixed': {}, 'varying': {}}
        os.makedirs(os.path.join(OUT, champ), exist_ok=True)
        json.dump(out, open(os.path.join(OUT, champ, f'{name}.json'), 'w'), indent=1)
        index.setdefault(champ, {})[name] = {'casts': len(ts)}
        print(f'{champ:10s} {name:40s} {len(ts):4d} attacks', flush=True)
    # releases: a spell that arms the next attack (118 in its cast tick) is undone at that attack's hit, in a tick of
    # the caster that holds 118 again (Darius W: 522, 271, 118 ff, 465, 71 x4, 65 ...)
    for champ, spells in list(index.items()):
        for spell, info in list(spells.items()):
            if 118 not in info.get('sequence', []):
                continue
            net = next(n for n, c in heroes.items() if c == champ)
            ts = sorted(casts_by_name.get((net, spell), []))
            rel = collections.Counter()
            rel_t = {}
            for t in ts:
                for k in sorted(kk for kk in by_tick if kk[1] == net and t + 0.05 < kk[0] <= t + 8.0)[:400]:
                    seq = tuple(x[2] for x in sorted(by_tick[k], key=lambda x: x[0]))
                    if 118 in seq:
                        rel[seq] += 1
                        rel_t.setdefault(seq, k[0])
                        break
            if not rel:
                continue
            seq, n = rel.most_common(1)[0]
            t = rel_t[seq]
            pk = sorted(by_tick[(round(t, 3), net)], key=lambda x: x[0])
            decoded = [{'pid': pid, 'ch': ch, 'who': 'caster', 'values': RW.decode(pid, net, body), 'raw': None}
                       for tt, ch, pid, body in pk]
            out = {'champion': champ, 'spell': spell + '__release', 'caster': net, 'target': None, 't': t,
                   'casts': len(ts), 'sequence': list(seq), 'sequence_cases': n, 'packets': decoded, 'fixed': {},
                   'varying': {}}
            json.dump(out, open(os.path.join(OUT, champ, f'{spell}__release.json'), 'w'), indent=1)
            print(f'{champ:10s} {spell + "__release":40s} sequence {list(seq)} in {n} of {len(ts)}', flush=True)
    path = os.path.join(OUT, 'index.json')
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(index)
    json.dump(old, open(path, 'w'), indent=1)
    print('->', path)


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
