"""Our server's spells against Riot's: every champion's Q / W / E / R cast offline by our server at an enemy champion
standing near, the packets it made set against what the real server sent after the same spell in the replays (the
spell's template, data/exe1620/spells16/<Champion>.json) - by mechanic, not by byte:

    cast     cast time / total time written in the 1215 [template's cast struct when the same in all casts]
    move     the caster dashed (1140) or was teleported (61 with a teleport id)
    missile  the cast's own missile left (938), missile spells were made (223)
    damage   the unit hit took damage (150: type, how many, when)
    control  crowd control on the unit hit (435 types 5 / 7 / 8 / 11 / 12 / 22 / 23 / 25 / 29 / 30 / 31 / 32 ...)
    self     buffs the caster got (435 by name hash), spells put in its slots (78 into slots 0-3 = recast forms)
    units    units created (626 / 1038)

    python tools/spell_conform16.py [Champion ..] [--workers n]   -> data/exe1620/spells16/conform.txt + conform.json
    python tools/spell_conform16.py show <Champion>               the two sides of each spell

A line per difference: `Champion Q Spell: <kind> real <...> ours <...>`. No client needed.
"""
import collections
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, ROOT)
os.environ.setdefault('BA_PATCH', '1620')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'spells16')
CC = {5: 'stun', 7: 'silence', 8: 'taunt', 11: 'slow', 12: 'snare', 22: 'fear', 23: 'charm', 25: 'suppress',
      29: 'flee', 30: 'knockup', 31: 'knockback', 32: 'disarm', 33: 'grounded', 34: 'drowsy', 35: 'asleep'}
WINDOW = 5.0


def f32(h):
    try:
        return struct.unpack('<f', bytes.fromhex(h))[0] if isinstance(h, str) and len(h) == 8 else None
    except Exception:
        return None


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and len(h) == 8 else None


def text(v):
    try:
        return bytes.fromhex(v['text']).decode('latin-1').rstrip('\0')
    except Exception:
        return ''


# ------------------------------------------------------------------------------------------------ the real side
def real_side(tpl, spell_hash):
    """a template -> the mechanics the real server showed after the cast"""
    c = (tpl.get('cast') or {}).get('+0x18') or {}
    out = {'samples': tpl['samples'], 'games': tpl.get('games', 0),
           'cast_time': f32(c.get('+0x4c')), 'total_time': f32(c.get('+0xa8')),
           'move': None, 'own_missile': None, 'missiles': [], 'damage': [], 'control': {}, 'self': {}, 'recast': [],
           'units': []}
    for e in tpl['events']:
        pid, role, share, dt = e['pid'], e['role'], e['share'], e['dt']
        v = e.get('values') if isinstance(e.get('values'), dict) else {}
        if role == 'caster' and share >= 0.5 and dt <= 2.5:
            if pid == 1140 and out['move'] is None:
                out['move'] = ('dash', dt)
            elif pid == 61 and v.get('teleport') is not None and out['move'] is None:
                out['move'] = ('teleport', dt)
        if role == 'caster' and pid == 938 and share >= 0.5 and out['own_missile'] is None and                 v.get('+0x10') == {'$': 'net', 'of': 'missile0'}:       # the cast's own missile, not a basic attack's
            out['own_missile'] = (dt, e.get('repeat', 1))
        if role == 'missile' and pid == 223 and share >= 0.5:
            out['missiles'].append((dt, e.get('repeat', 1), (v.get('+0xf8') or {}).get('+0x18')))
        if role == 'other' and pid == 150 and share >= 0.3:
            out['damage'].append((dt, int(v.get('+0x18', '0') or '0', 16) if isinstance(v.get('+0x18'), str) else None,
                                  e.get('repeat', 1), v.get('+0x2c') == spell_hash, share))
        if role == 'other' and pid == 435 and share >= 0.25 and isinstance(v.get('+0x38'), str) and not e.get('amb'):
            k = CC.get(int(v['+0x38'], 16))
            if k:
                d = f32(v.get('+0x3c')) if isinstance(v.get('+0x3c'), str) else None
                out['control'][k] = (dt, d, share)
        if role == 'caster' and pid == 435 and share >= 0.5 and isinstance(v.get('+0x64'), str) and dt <= WINDOW - 0.5:
            out['self'][v['+0x64']] = (dt, int(v['+0x38'], 16) if isinstance(v.get('+0x38'), str) else None)
        if role == 'caster' and pid == 78 and share >= 0.5 and isinstance(v.get('+0x10'), dict) and dt <= WINDOW - 0.5:
            sl = int(v['+0x10'].get('+0xf', 'ff'), 16)
            if sl < 4:
                out['recast'].append((dt, sl, text(v.get('+0x20', {}))))
        if role == 'spawn' and pid in (626, 1038) and share >= 0.5:
            out['units'].append((dt, text(v.get('+0x38' if pid == 626 else '+0x10', {})) or '?'))
    return out


# ------------------------------------------------------------------------------------------------ our side
def our_side(champ, enemy='Garen'):
    """{spell: mechanics} of the champion's four spells as our server plays them"""
    from core.session import Session
    from core.game import DT
    import pkt_schema as PS
    import waypoints
    import forms16
    from core import spells as S
    logs = []
    foe_name = enemy if enemy != champ else 'Darius'
    roster = [{'champion': champ}] + [{} for _ in range(4)] + [{'champion': foe_name}] + [{} for _ in range(4)]
    s = Session(roster, log=logs.append, options={'no_fog': True})
    g = s.game
    g.start_packets()
    me, foe = s.player, g.heroes[5]
    for h in g.heroes:
        h.brain = None
    me.add_xp(g.data['xp_per_level'][16] + 1)
    for _ in range(18):
        for slot in (3, 0, 1, 2):
            me.level_spell(slot)
    res = {}
    for slot in range(4):
        # everything of the last spell ends before the next one begins
        t_quiet = g.t + 14.0
        while g.t < t_quiet:
            g.step(DT)
        me.teleport((7000.0, 7000.0))
        inf = S.info(me.champ, me.champ.spells[slot])
        rank = max(1, me.spell_levels[slot])
        if inf.targeting in S.SELF_TYPES:
            far = max(100.0, min(250.0, 0.6 * (inf.radius(rank) or 250.0)))      # inside what a spell around its caster reaches
        else:
            far = max(100.0, min(350.0, 0.7 * inf.range(rank)))
        foe.teleport((7000.0 + far, 7000.0))
        foe.set_hp(foe.max_hp)
        if not me.alive or not foe.alive:
            break
        for _ in range(3):                               # the teleports' own packets are not the spell's
            g.step(DT)
        me.cooldowns = [0.0] * 6
        me.set_par(me.max_par)
        me.slot_names = list(me.champ.spells)
        name = me.champ.spells[slot]
        n0 = len(logs)
        t0 = g.t
        known = set(g.units)
        ans = g.spells.request(me, {'slot': slot, 'target': foe.net, 'target_place': foe.pos, 'cursor': foe.pos,
                                    'caster_place': me.pos, 'flags': 0, 'hash': 0})
        o = {'answer': str(ans), 'cast_time': None, 'total_time': None, 'move': None, 'own_missile': None, 'missiles': [],
             'damage': [], 'control': {}, 'self': {}, 'recast': [], 'units': [], 'errors': [], 'ids': collections.Counter()}
        while g.t < t0 + WINDOW:
            pk = g.step(DT)
            dt = round(g.t - t0 - DT, 3)
            flat = []
            for ch, pid, net, body in pk:
                if pid == 239:                           # a container: the packets inside it
                    try:
                        flat += [(ch, p2, n2, b2) for p2, n2, b2 in forms16.unpack(PS.parse(g.pk.schema(239), body))]
                    except Exception:
                        pass
                else:
                    flat.append((ch, pid, net, body))
            for ch, pid, net, body in flat:
                o['ids'][pid] += 1
                if pid not in (1215, 1140, 61, 938, 223, 150, 435, 78, 626, 1038):
                    continue
                try:
                    v = PS.parse(g.pk.schema(pid), body)
                except Exception:
                    v = None
                v = v if isinstance(v, dict) else {}
                if pid == 1215 and net == me.net and o['cast_time'] is None:
                    c = v.get('+0x18') or {}
                    o['cast_time'], o['total_time'] = f32(c.get('+0x4c')), f32(c.get('+0xa8'))
                    o['missile0'] = c.get('+0xbc')
                elif pid == 1140 and o['move'] is None:
                    raw = bytes.fromhex((v.get('+0x18') or {}).get('text', ''))
                    if struct.pack('<I', me.net) in raw[:8]:
                        o['move'] = ('dash', dt)
                elif pid == 61 and o['move'] is None:
                    try:
                        es = [x for x in waypoints.parse(bytes.fromhex(v['+0x18']['text'])) if x['net'] == me.net]
                    except Exception:
                        es = []
                    if es and es[0].get('teleport') is not None:
                        o['move'] = ('teleport', dt)
                elif pid == 938 and net == me.net and o['own_missile'] is None and v.get('+0x10') == o.get('missile0'):
                    o['own_missile'] = (dt, 1)
                elif pid == 223:
                    o['missiles'].append((dt, 1, (v.get('+0xf8') or {}).get('+0x18')))
                elif pid == 150 and net == foe.net:
                    o['damage'].append((dt, int(v.get('+0x18', '00'), 16) if isinstance(v.get('+0x18'), str) else None))
                elif pid == 435 and net == foe.net and isinstance(v.get('+0x38'), str):
                    k = CC.get(int(v['+0x38'], 16))
                    if k:
                        o['control'][k] = (dt, f32(v.get('+0x3c')), 1.0)
                elif pid == 435 and net == me.net and isinstance(v.get('+0x64'), str):
                    o['self'][v['+0x64']] = (dt, int(v['+0x38'], 16) if isinstance(v.get('+0x38'), str) else None)
                elif pid == 78 and net == me.net and isinstance(v.get('+0x10'), dict):
                    sl = int(v['+0x10'].get('+0xf', 'ff'), 16)
                    if sl < 4:
                        o['recast'].append((dt, sl, text(v.get('+0x20', {}))))
                elif pid in (626, 1038) and net not in known:
                    known.add(net)
                    o['units'].append((dt, text(v.get('+0x38' if pid == 626 else '+0x10', {})) or '?'))
        o['errors'] = [x for x in logs[n0:] if 'template' in x or 'Traceback' in x][:6]
        o['ids'] = dict(o['ids'])
        res[name] = o
    return res


# ------------------------------------------------------------------------------------------------ the comparison
def differences(real, ours):
    """[(kind, text)] where the two sides disagree on a mechanic"""
    d = []
    if 'casts ' not in ours['answer']:
        d.append(('refused', ours['answer'][:90]))
        return d
    for e in ours['errors']:
        d.append(('error', e[:140]))
    if real is None:
        return d
    for k, tol in (('cast_time', 0.04), ('total_time', 0.3)):
        a, b = real.get(k), ours.get(k)
        if a is not None and b is not None and abs(a - b) > tol:
            d.append((k, f'real {a:.3f} ours {b:.3f}'))
    rm, om = real['move'], ours['move']
    if (rm and rm[0]) != (om and om[0]):
        d.append(('move', f'real {rm[0] + f" +{rm[1]:.2f}" if rm else "none"} ours {om[0] + f" +{om[1]:.2f}" if om else "none"}'))
    elif rm and om and abs(rm[1] - om[1]) > 0.12:
        d.append(('move_time', f'real +{rm[1]:.2f} ours +{om[1]:.2f}'))
    ra, oa = real['own_missile'], ours['own_missile']
    if bool(ra) != bool(oa):
        d.append(('own_missile', f'real {"+%.2f" % ra[0] if ra else "none"} ours {"+%.2f" % oa[0] if oa else "none"}'))
    elif ra and oa and abs(ra[0] - oa[0]) > 0.12:
        d.append(('own_missile_time', f'real +{ra[0]:.2f} ours +{oa[0]:.2f}'))
    rh = sorted({m[2] for m in real['missiles'] if m[2]})
    oh = sorted({m[2] for m in ours['missiles'] if m[2]})
    if rh != oh:
        d.append(('missile_spells', f'real {len(rh)} {rh[:4]} ours {len(oh)} {oh[:4]}'))
    else:
        for h in rh:
            a = min(m[0] for m in real['missiles'] if m[2] == h)
            b = min(m[0] for m in ours['missiles'] if m[2] == h)
            if abs(a - b) > 0.12:
                d.append(('missile_time', f'{h} real +{a:.2f} ours +{b:.2f}'))
    own = [x for x in real['damage'] if x[3]]
    if own and not ours['damage']:
        d.append(('damage', f'real +{own[0][0]:.2f} type {own[0][1]} x{own[0][2]} ({own[0][4] * 100:.0f}%) ours none'))
    elif not real['damage'] and ours['damage'] and real['samples'] >= 12:
        d.append(('damage_extra', f'real none in {real["samples"]} casts, ours +{ours["damage"][0][0]:.2f} x{len(ours["damage"])}'))
    elif own and ours['damage']:
        a, b = own[0], ours['damage'][0]
        flies = real['own_missile'] or real['missiles'] or ours['own_missile'] or ours['missiles']
        if abs(a[0] - b[0]) > 0.25 and not flies:        # a missile's hit time is the distance's
            d.append(('damage_time', f'real +{a[0]:.2f} ours +{b[0]:.2f}'))
        if a[1] is not None and b[1] is not None and a[1] != b[1]:
            d.append(('damage_type', f'real {a[1]} ours {b[1]}'))
    rc, oc = set(real['control']), set(ours['control'])
    if rc != oc:
        d.append(('control', f'real {sorted(rc)} ours {sorted(oc)}'))
    else:
        for k in rc:
            a, b = real['control'][k][1], ours['control'][k][1]
            if a is not None and b is not None and abs(a - b) > 0.15 and a < 100:
                d.append(('control_time', f'{k} real {a:.2f} s ours {b:.2f} s'))
    rs, os_ = set(real['self']), set(ours['self'])
    if rs - os_:
        d.append(('self_buff_missing', f'{sorted(rs - os_)[:4]}'))
    if os_ - rs and real['samples'] >= 6:
        d.append(('self_buff_extra', f'{sorted(os_ - rs)[:4]}'))
    rr, orr = sorted({(x[1], x[2]) for x in real['recast']}), sorted({(x[1], x[2]) for x in ours['recast']})
    if rr != orr:
        d.append(('recast', f'real {rr} ours {orr}'))
    ru, ou = sorted(x[1] for x in real['units']), sorted(x[1] for x in ours['units'])
    if ru != ou:
        d.append(('units', f'real {ru} ours {ou}'))
    return d


def check(champ):
    sys.path.insert(0, ROOT)
    from server.core import packets as P
    from server.core import templates as T
    tpls = T.load(champ)
    ours = our_side(champ)
    rows = []
    for i, (spell, o) in enumerate(ours.items()):
        t = tpls.get(spell) or next((v for k, v in tpls.items() if k.lower() == spell.lower()), None)
        r = real_side(t, P.u32(P.elf(spell))) if t else None
        rows.append({'champion': champ, 'slot': 'QWER'[i], 'spell': spell, 'real': r, 'ours': o, 'diff': differences(r, o)})
    return rows


def worker(champs, q):
    for c in champs:
        try:
            q.put((c, check(c)))
        except Exception as e:
            import traceback
            q.put((c, [{'champion': c, 'slot': '-', 'spell': '-', 'real': None, 'ours': None,
                        'diff': [('crash', repr(e)[:100] + ' | ' + ' | '.join(traceback.format_exc().splitlines()[-3:])[:260])]}]))


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == 'show':
        for r in check(argv[1]):
            print(f"== {r['champion']} {r['slot']} {r['spell']}")
            for side in ('real', 'ours'):
                x = r[side]
                print(f'   {side}:', json.dumps({k: v for k, v in (x or {}).items() if k != 'ids'}, default=str)[:900])
            for k, tx in r['diff']:
                print(f'   DIFF {k}: {tx}')
        return
    workers = 6
    if '--workers' in argv:
        i = argv.index('--workers')
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    champs = [a for a in argv if not a.startswith('--')]
    if not champs:
        from server.core import gamedata as G
        champs = [c['alias'] for c in G.champion_index()]
    import multiprocessing as mp
    q = mp.Queue()
    procs = [mp.Process(target=worker, args=(champs[i::workers], q)) for i in range(workers) if champs[i::workers]]
    for p in procs:
        p.start()
    allrows = []
    for k in range(len(champs)):
        c, rows = q.get()
        allrows += rows
        print(f'{k + 1}/{len(champs)} {c}: {sum(len(r["diff"]) for r in rows)} differences', flush=True)
    for p in procs:
        p.join()
    allrows.sort(key=lambda r: (r['champion'], 'QWER-'.index(r['slot'])))
    lines, kinds = [], collections.Counter()
    spells = clean = no_tpl = 0
    for r in allrows:
        spells += 1
        no_tpl += r['real'] is None
        clean += not r['diff'] and r['real'] is not None
        for k, tx in r['diff']:
            kinds[k] += 1
            lines.append(f"{r['champion']:14s} {r['slot']} {r['spell']:28s} {k:18s} {tx}")
    head = [f'{spells} spells: {clean} agree with the replays on every mechanic checked, {no_tpl} have no template',
            'differences by kind: ' + ', '.join(f'{k} {n}' for k, n in kinds.most_common()), '']
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'conform.txt'), 'w', encoding='utf-8').write('\n'.join(head + lines) + '\n')
    json.dump(allrows, open(os.path.join(OUT, 'conform.json'), 'w'), default=str)
    print('\n'.join(head[:2]))


if __name__ == '__main__':
    main()
