"""Facts of a real 12.23 match, from Riot's server packets (maknee's decoded replays, research/replays1223/*.jsonl.gz):
what each lane minion is (its barracks, wave and place in the wave), when it came, and every hit between minions,
turrets and champions with its exact damage. These are the numbers our server must reproduce.

  python tools/replay_facts.py <batch.jsonl.gz> [game index] [out.json]

Minion kinds come from the wave order the level script gives (SpawnOrderMinionNames: Super, Melee, Cannon, Caster):
inside one barracks' wave the minions arrive in that order, so the first ones are melee, then the cannon when the wave
has one, then the casters; a 6-minion wave is 3 melee + 3 casters, a 7-minion wave has the cannon 4th.
"""
import collections
import gzip
import json
import sys


def load(path, index):
    with gzip.open(path, 'rt', encoding='utf8') as f:
        for i, line in enumerate(f):
            if i == index:
                return json.loads(line)['events']
    raise SystemExit('no game %d' % index)


def facts(events):
    turrets, heroes = {}, {}
    waves = collections.defaultdict(list)  # (barracks, wave) -> [(time, minion)]
    for e in events:
        k, v = next(iter(e.items()))
        if k == 'CreateTurret':
            turrets[v['net_id']] = v['name']
        elif k == 'CreateHero':
            heroes[v['net_id']] = v['champion']
        elif k == 'BarrackSpawnUnit':
            waves[(v['barrack_net_id'], v['wave_count'])].append((v['time'], v['minion_net_id'], v['minion_type']))
    minions = {}
    for (barracks, wave), ms in waves.items():
        ms.sort()
        n = len(ms)
        # supers come first and change the count; we only label plain 6- and 7-minion waves
        kinds = ['Melee'] * 3 + (['Cannon'] if n == 7 else []) + ['Caster'] * 3 if n in (6, 7) else ['?'] * n
        for (t, mid, mtype), kind in zip(ms, kinds):
            minions[mid] = {'barracks': barracks, 'wave': wave, 'kind': kind, 'spawn': t, 'type_hash': mtype}

    def who(net):
        if net in minions:
            m = minions[net]
            return 'minion', '%s w%d' % (m['kind'], m['wave'])
        if net in turrets:
            return 'turret', turrets[net]
        if net in heroes:
            return 'hero', heroes[net]
        return 'other', str(net)

    hits = []
    for e in events:
        k, v = next(iter(e.items()))
        if k != 'UnitApplyDamage':
            continue
        sk, sn = who(v['source_net_id'])
        tk, tn = who(v['target_net_id'])
        hits.append({'t': v['time'], 'source': v['source_net_id'], 'target': v['target_net_id'], 'source_kind': sk, 'source_is': sn,
                     'target_kind': tk, 'target_is': tn, 'damage': v['damage']})
    return {'turrets': turrets, 'heroes': heroes, 'minions': minions, 'hits': hits}


def main():
    path = sys.argv[1]
    index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    f = facts(load(path, index))
    print('%d turrets, %d heroes, %d lane minions, %d hits' % (len(f['turrets']), len(f['heroes']), len(f['minions']), len(f['hits'])))
    # spawn times of the first waves (one barracks)
    by_barracks = collections.defaultdict(list)
    for mid, m in f['minions'].items():
        by_barracks[m['barracks']].append((m['spawn'], m['wave'], m['kind']))
    first = sorted(by_barracks)[0]
    print('barracks %d, first 3 waves:' % first)
    for t, w, kind in sorted(by_barracks[first])[:21]:
        print('   wave %2d  %8.3f s  %s' % (w, t, kind))
    # minion-on-minion and turret-on-minion damage by attacker kind, target kind and the attacker's wave
    table = collections.defaultdict(list)
    for h in f['hits']:
        if h['target_kind'] != 'minion':
            continue
        if h['source_kind'] == 'minion':
            sk, sw = h['source_is'].split(' w')
            tk, tw = h['target_is'].split(' w')
            table[('minion', sk, tk, int(sw))].append(h['damage'])
        elif h['source_kind'] == 'turret':
            tk, tw = h['target_is'].split(' w')
            table[('turret', h['source_is'][:13], tk, int(tw))].append(h['damage'])
    print('damage between units (attacker kind, target kind, wave): distinct values')
    for key in sorted(table)[:80]:
        vals = sorted(set(round(x, 3) for x in table[key]))
        print('  %-6s %-14s -> %-7s wave %2d: %4d hits, values %s' % (key[0], key[1], key[2], key[3], len(table[key]), vals[:6]))
    if len(sys.argv) > 3:
        json.dump(f, open(sys.argv[3], 'w'), indent=0)


if __name__ == '__main__':
    main()
