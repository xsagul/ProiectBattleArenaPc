"""What our 16.20 server takes from the recorded live match, extracted once into data/exe1620/ so the server needs
neither the 45 MB recording nor the emulator at run time:

  start16.pkl    the recording's own start: part 0 (clock, game info), part 1 (the start state), the first second of
                 part 2 (the world's first state), the loading answers, the map script's packets of the first 30 s,
                 each champion's creation data and what the real server sent when it first came into sight
  forms16.json   one decoded sample per packet form the server writes (a template: the server changes the fields
                 it knows and keeps the rest), the minion spawn / way-out data, the structures' net ids

    python tools/build_forms16.py [data/live/<gameId>]
"""
import json
import os
import pickle
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
import livedb          # noqa: E402

OUT = os.path.join(ROOT, 'data', 'exe1620')
INIT = 1.0             # seconds of part 2 kept as "the world's first state"
DROP = {1007, 1095}


def main():
    game = sys.argv[1] if len(sys.argv) > 1 else livedb.DEFAULT
    L = livedb.Live(game)
    g = L.gates
    t1, t2 = g[1] - g[2], 0.0                      # part 1 begins / part 2 begins, in game time
    part0, part1, init, loading, timeline = [], [], [], [], []
    for t, way, ch, pid, net, body in L.rows:
        if way != 'S':
            continue
        if pid == 1095:
            loading.append((ch, pid, net, body))
        if pid in DROP:
            continue
        if t < t1:
            part0.append((ch, pid, net, body))
        elif t < t2:
            part1.append((ch, pid, net, body))
        elif t < INIT:
            init.append((t, ch, pid, net, body))
        elif t < 30.0 and pid in (984, 302):
            timeline.append((t, ch, pid, net, body))
    heroes = []
    for i, (ch, pid, net, body) in enumerate(part1):
        if pid == 222:
            v = L.parse(222, body)
            x, y, z = livedb.vec3(v['+0x20'])
            heroes.append({'net': livedb.u32(v['+0x1c']), 'index': i, 'values': v, 'pos': (x, z), 'height': y,
                           'champion': bytes.fromhex(v['+0x38']['text']).decode(), 'team': 100 if v['+0x12'] == '01' else 200,
                           'name': bytes.fromhex(v['+0x58']['text']).decode(), 'bot': v['+0x52'] == '01'})
    nets = {h['net'] for h in heroes}
    # what the real server sent when a champion first came into the player's sight (one tick): container + health +
    # cooldowns + buffs; taken as the form of "a champion enters sight"
    enter = {}
    for h in heroes:
        t0, out = None, []
        for t, way, ch, pid, net, body in L.s2c(None, 0.0):
            if t0 is None and net == h['net'] and pid == 239:
                t0 = t
            if t0 is not None:
                if t > t0 + 0.0005:
                    break
                if net == h['net'] and pid in (239, 684, 635, 904):
                    out.append((ch, pid, net, body))
        enter[h['net']] = (t0, out)
    # every champion's replicated values in the first seconds (the full state the real server sets)
    values = {h['net']: {} for h in heroes}
    for t, way, ch, pid, net, body in L.s2c(287, 0.0, 12.0):
        for n, vals in L.repl(body, cls_of=lambda n: 'AIHero' if n in nets else None) if False else []:
            pass
    import replication
    import repl16
    # the state of the last moment before anything happens (14 s: the pre-game locks are off, nothing is bought
    # by the bots' values we keep: gold / items / stats are replaced by the server's own anyway)
    for t, way, ch, pid, net, body in L.s2c(287, 0.0, 14.0):
        v = L.parse(287, body)
        for n, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
            if n in nets:
                values[n].update(repl16.read_unit(groups, 'AIHero'))
    pickle.dump({'source': os.path.basename(os.path.normpath(game)), 'part0': part0, 'part1': part1, 'init': init,
                 'loading': loading, 'timeline': timeline, 'heroes': heroes, 'enter': enter, 'hero_values': values,
                 'gates': g}, open(os.path.join(OUT, 'start16.pkl'), 'wb'), protocol=4)
    print(f'start16.pkl: part 0 {len(part0)}, part 1 {len(part1)}, init {len(init)}, loading {len(loading)}, timeline {len(timeline)}, '
          f'{len(heroes)} champions; entering sight: ' + ', '.join(f"{h['champion']} {len(enter[h['net']][1])}" for h in heroes))

    # ---------------------------------------------------------------- forms
    forms = {}

    def take(name, pid, pred=None, a=0.0, b=None, raw=False):
        for t, way, ch, p, net, body in L.s2c(pid, a, b):
            v = L.parse(pid, body)
            if v is None:
                continue
            if pred is None or pred(v, net):
                forms[name] = {'pid': pid, 'values': v, 'net': net, 't': round(t, 3)}
                return v
        print('   no sample for', name, pid)

    hero = lambda v, net: net in nets
    not_hero = lambda v, net: net not in nets
    take('attack_minion', 390, lambda v, net: isinstance(v.get('+0x10'), dict) and '+0x1c' in v['+0x10'])
    take('attack_hero', 906, lambda v, net: net in nets and v['+0x10']['+0x28'] == [])
    take('attack_aim', 972, lambda v, net: v['+0x20'] == '02')
    take('missile_launch', 938)
    take('missile_object', 743)
    take('missile_end', 118)
    take('attack_done', 515, lambda v, net: v['+0x10'] == '01')
    take('attack_stop', 515, lambda v, net: v['+0x10'] == '00')
    take('target', 447)
    take('damage', 150)
    take('death', 1112, not_hero)
    take('delete', 1090)
    take('gold', 818)
    take('xp', 1024)
    take('level_up', 969)
    take('skill_level', 810, None, 1.0)
    take('face', 1201)
    take('cast', 1215, lambda v, net: net in nets and v['+0x18']['+0x60'] in ('00', '01', '02', '03'))
    take('cooldown', 635, None, 5.0)
    take('animation', 1088, hero)
    take('buff_add', 435, hero, 30.0)
    take('buff_count', 430, hero, 30.0)
    take('buff_remove', 262, hero, 30.0)
    take('spell_missile', 223)
    take('spell_slot', 78, hero, 30.0)
    take('anim_states', 904, hero, 30.0)
    take('item_bought', 63, None, 5.0)
    take('item_count', 1122)
    take('item_removed', 1237, None, 5.0)
    take('xp_orb', 1168)
    take('recall', 331)
    take('respawn', 158)
    take('score', 437)
    take('announce', 210)
    take('dash', 1140)
    take('stats_update', 121)
    world = json.load(open(os.path.join(game, 'world16.json')))
    forms['minion'] = {'spawn': {k: v['fields'] for k, v in world['spawn'].items()},
                       'blocks': {k: v['blocks'] for k, v in world['spawn'].items()},
                       'enter': world['enter'], 'barracks': {k: {'team': v['team'], 'lane': v['lane']} for k, v in world['barracks'].items()}}
    forms['turrets'] = json.load(open(os.path.join(game, 'turrets.json')))
    # the structures' replicated values as the real server first sets them (health, damage, armor, targetable)
    import structures16
    cls = {d['net']: 'AITurretCommon' for d in forms['turrets']}
    for net, (team, lane, tier, pos) in structures16.OTHERS.items():
        cls[net] = 'HQCommon' if tier == 'hq' else 'BarracksDampenerCommon'
    sv = {}
    for t, way, ch, pid, net, body in L.s2c(287, 0.0, 300.0):
        v = L.parse(287, body)
        for n, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
            if n in cls:
                try:
                    for k, x in repl16.read_unit(groups, cls[n]).items():
                        sv.setdefault(f'{n:x}', {}).setdefault(k, x)
                except Exception:
                    pass
    forms['structure_values'] = sv
    forms['others'] = {f'{net:x}': {'team': team, 'lane': lane, 'tier': tier, 'pos': pos} for net, (team, lane, tier, pos) in structures16.OTHERS.items()}
    # jungle: every monster the real server created (568), by its name "<Character>.<camp>.<index>": the first
    # creation's values as the form, and all its creation times; the packets that go with a creation
    jungle = {}
    for t, way, ch, pid, net, body in L.s2c(568):
        v = L.parse(568, body)
        name = bytes.fromhex(v['+0x10']['text']).decode('latin1')
        e = jungle.setdefault(name, {'values': v, 'times': [], 'pos': [round(c, 1) for c in livedb.vec3(v['+0x20'])],
                                     'character': bytes.fromhex(v['+0xb0']['text']).decode('latin1'),
                                     'camp': livedb.u32(v['+0x4c']), 'side': livedb.u32(v['+0x98']),
                                     'anim': bytes.fromhex(v['+0x70']['text']).decode('latin1')})
        e['times'].append(round(t, 2))
    unit514 = {}
    for t, way, ch, pid, net, body in L.s2c(514):
        v = L.parse(514, body)
        if v:
            unit514.setdefault(livedb.u32(v['+0x18']), v)
    for t, way, ch, pid, net, body in L.s2c(568):
        v = L.parse(568, body)
        name = bytes.fromhex(v['+0x10']['text']).decode('latin1')
        if 'camp_unit' not in jungle[name] and net in unit514:
            jungle[name]['camp_unit'] = unit514[net]
    forms['jungle'] = jungle
    take('camp_unit', 514)
    take('unit_on', 967, lambda v, net: v['+0x11'] == '01')
    # a monster's replicated values right after its creation (the form of the first block)
    mon_first = {}
    for t, way, ch, pid, net, body in L.s2c(568):
        mon_first.setdefault(net, t)
    mv = {}
    for t, way, ch, pid, net, body in L.s2c(287, 50.0, 400.0):
        v = L.parse(287, body)
        for n, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
            if n in mon_first and t - mon_first[n] < 12.0:
                try:
                    mv.setdefault(f'{n:x}', {}).update(repl16.read_unit(groups, 'lane_minion'))
                except Exception:
                    pass
    forms['monster_values'] = mv
    json.dump(forms, open(os.path.join(OUT, 'forms16.json'), 'w'), indent=1)
    print(f'forms16.json: {len(forms)} forms: ' + ' '.join(sorted(forms)))
    # the recipes (events16.json) beside them
    import shutil
    if os.path.exists(os.path.join(game, 'events16.json')):
        shutil.copy(os.path.join(game, 'events16.json'), os.path.join(OUT, 'recipes16.json'))
        print('recipes16.json copied')


if __name__ == '__main__':
    main()
