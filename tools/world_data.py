"""What our own world (server/world.py) takes from the 13.3 replay besides the lanes, gathered once into
data/exe133/world_data.json:

  minion_blocks  per minion kind (98 +0x14: 04 melee, 05 caster, 06 cannon): the two replication blocks Riot's server
                 sends for a new lane minion -- A in the tick of its creation, B 0.132 s later (groups 2, 3, 5: what it
                 may do, health, attack range, move speed, "can be targeted"). Raw groups {group: [mask, hex]}.
  turrets        the 24 turrets of the keyframe: net id, name, team, lane, tier, position, health, armor, damage (the
                 replay's values at 0.37 s)
  monsters       the jungle: every monster name's first creation in the replay (359 with its place, name and skin; the
                 506 x4 before it, 518 / 770 / 387 after it; its first replication blocks, raw) -- sent again as they are
  champions      the ten champions of the start state: net id, champion, team, place, and what Riot's server said
                 they may do during the first 12 s (ActionState ...)
  templates      real packet bodies our world rewrites with its own ids: a turret's attack (740 target, 66, 592 first
                 attack, 26 next attack, 516, 779 missile, 490 stop), a turret's death (310, 65, 71)
                 and a champion's death (780 + 417 death time, 440, 568) and return (128: place, mana)

Positions of the turrets, inhibitors and nexuses: the map's own object positions (the same numbers LeagueSandbox's
Map11 level script lists; checked against the attacker positions of the replay's turret attacks where a turret
attacked).

  world_data.py        build the file
"""
import collections
import gzip
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
import lol_packets as LP  # noqa: E402
import replication as RP  # noqa: E402
import repl_codec as RC  # noqa: E402
import rofl_packets as R  # noqa: E402

RES = os.path.join(ROOT, 'data', 'exe133')
OUT = os.path.join(RES, 'world_data.json')
ROFL = os.path.join(ROOT, 'data', 'rofl', 'KR-6363178603_13.3.rofl')

POSITIONS = {
    'Turret_T1_R_03_A': (10504.246, 1029.7169), 'Turret_T1_R_02_A': (6919.156, 1483.5986),
    'Turret_T1_C_07_A': (4281.712, 1253.5687), 'Turret_T2_R_03_A': (13866.243, 4505.2236),
    'Turret_T2_R_02_A': (13327.417, 8226.276), 'Turret_T2_R_01_A': (13624.748, 10572.771),
    'Turret_T1_C_05_A': (5846.0967, 6396.7505), 'Turret_T1_C_04_A': (5048.0703, 4812.8936),
    'Turret_T1_C_03_A': (3651.9016, 3696.424), 'Turret_T1_C_01_A': (1748.2611, 2270.7068),
    'Turret_T1_C_02_A': (2177.64, 1807.6298), 'Turret_T2_C_05_A': (8955.434, 8510.48),
    'Turret_T2_C_04_A': (9767.701, 10113.608), 'Turret_T2_C_03_A': (11134.814, 11207.938),
    'Turret_T2_C_01_A': (13052.915, 12612.381), 'Turret_T2_C_02_A': (12611.182, 13084.111),
    'Turret_OrderTurretShrine_A': (105.92846, 134.49403), 'Turret_ChaosTurretShrine_A': (14576.36, 14693.827),
    'Turret_T1_L_03_A': (981.28345, 10441.454), 'Turret_T1_L_02_A': (1512.892, 6699.57),
    'Turret_T1_C_06_A': (1169.9619, 4287.4434), 'Turret_T2_L_03_A': (4318.3037, 13875.8),
    'Turret_T2_L_02_A': (7943.152, 13411.799), 'Turret_T2_L_01_A': (10481.091, 13650.535),
}
# the lane of the turrets whose name says C but stand on a side lane's inhibitor (and the nexus pair)
LANES = {'Turret_T1_C_07_A': 'bot', 'Turret_T1_C_06_A': 'top', 'Turret_T1_C_03_A': 'mid',
         'Turret_T1_C_01_A': 'nexus', 'Turret_T1_C_02_A': 'nexus', 'Turret_T2_C_01_A': 'nexus',
         'Turret_T2_C_02_A': 'nexus'}
STRUCTURES = {
    'inhibitors': {'Barracks_T1_L1': (1171.8285, 3571.784), 'Barracks_T1_C1': (3203.0286, 3208.784),
                   'Barracks_T1_R1': (3452.5286, 1236.884), 'Barracks_T2_L1': (11261.665, 13676.563),
                   'Barracks_T2_C1': (11598.124, 11667.8125), 'Barracks_T2_R1': (13604.601, 11316.011)},
    'nexus': {'HQ_T1': (1551.3535, 1659.627), 'HQ_T2': (13142.73, 12964.941)},
    'fountain': {'blue': (394.76892, 461.57095), 'red': (14340.419, 14391.075)},
}
ATTACKER = 0x4000000b         # the blue mid outer turret: its first fight of the replay (65.2 .. 69.2 s)
DEAD = 0x40000008             # the red bot outer turret: the replay's first turret to fall (654.64 s)
VICTIM = 0x40000023           # Jax: killed at 308.379 s (death time 14 s), alive again at 322.393 s
NEXUS = {'red': 0xfff02c0f, 'blue': 0xfff97db5}   # 5500 health each; the red one fell to Nidalee (blue) at 1863.668 s


def keyframe_turrets():
    out = {}
    for line in gzip.open(os.path.join(RES, 'decoded_13.3_key1.jsonl.gz'), 'rt'):
        r = json.loads(line)
        if r['id'] == 565:
            s = collections.defaultdict(bytearray)
            for blk, off, hx, _ in r['f']:
                if blk >= 1:
                    s[blk] += bytes.fromhex(hx)
            out[r['obj']] = [bytes(s[k]).split(b'\0')[0].decode('latin1') for k in sorted(s)]
    return out


def read_values(groups, table):
    out = {}
    for g, (mask, data) in groups.items():
        at = 0
        for b in range(32):
            if not mask >> b & 1:
                continue
            name, kind = table.get((g, b), (f'g{g}b{b}', 'i'))
            end = RP.take(data, at, kind)
            raw, at = data[at:end], end
            if kind == 'f':
                out[name] = 0.0 if raw == b'\xff' else struct.unpack('<f', raw[-4:])[0]
            else:
                v, sh = 0, 0
                for c in raw:
                    v |= (c & 0x7f) << sh
                    sh += 7
                out[name] = v
    return out


def main():
    names = keyframe_turrets()
    tnames = {(g, b): (n, k) for n, (g, b, k) in RC.names('turret').items()}
    spawn = {}
    for line in open(os.path.join(RES, 'codec', '98.all.jsonl')):
        r = json.loads(line)
        if r['v']:
            spawn[r['obj']] = (r['t'], r['v']['+0x14'], int(r['v']['+0x15'], 16))
    blocks = collections.defaultdict(list)        # net -> [(dt, groups)]
    tvals = collections.defaultdict(dict)
    tpl = collections.defaultdict(list)
    import pkt_schema as PS
    import pkt_tree as PT
    sc359, tr359 = PS.Schema.load(359), PT.Tree(359)
    sc770, tr770 = PS.Schema.load(770), PT.Tree(770)
    neutral = {}                                  # net -> the monster's creation and what followed in its first second
    tick506, tick_t = collections.defaultdict(list), None
    heroes = {h['net_id']: h for h in json.load(open(os.path.join(RES, 's2c_79_heroes.json'), encoding='utf8'))}
    hnames = {(g, b): (n, k) for n, (g, b, k) in RC.names().items()}
    hero_state = collections.defaultdict(dict)   # net -> what the server said it may do in the first 12 s
    for e, (t, ch, pid, obj, body) in R.stream(R.Rofl(ROFL), (1, 2)):
        if e['type'] == 2 and e['id'] != 1:
            continue
        if t > 660:
            # after the first eleven minutes only the end of the match is wanted: the red nexus falls at 1863.668 s
            # (634 with the killer; 589 SOG_NEXUS, 785, 716), then 766 (1867.65) and 137 + 213 (1868.84)
            if t >= 1863.6:
                if obj == NEXUS['red'] and pid == 634:
                    tpl['end_634'].append([ch, bytes(body).hex()])
                elif obj == 0 and pid in (589, 785, 716, 766, 137, 213) and not tpl[f'end_{pid}']:
                    tpl[f'end_{pid}'].append([ch, bytes(body).hex()])
            continue
        if t != tick_t:
            tick506.clear()
            tick_t = t
        if pid == 506:
            tick506[obj].append([0.0, ch, pid, bytes(body).hex()])
        if pid == 359:
            v = PS.decode(tr359, sc359, struct.pack('<HI', 359, obj) + body)
            if v is not None:
                neutral[obj] = dict(net=obj, t=t, packets=list(tick506.get(obj, [])), blocks=[],
                                    create=dict(pid=359, ch=ch, body=bytes(body).hex(), value=v))
        elif obj in neutral and t - neutral[obj]['t'] < 1.0 and pid in (518, 770, 387):
            neutral[obj]['packets'].append([round(t - neutral[obj]['t'], 3), ch, pid, bytes(body).hex()])
            if pid == 770 and 'hp' not in neutral[obj]:
                v = PS.decode(tr770, sc770, struct.pack('<HI', 770, obj) + body)
                if v is not None:
                    neutral[obj]['hp'] = struct.unpack('<f', bytes.fromhex(v['+0x10']['text'])[8:12])[0]
        if pid == 595:
            sp = LP.split_595(body)
            if not sp:
                continue
            try:
                units = RP.parse(sp[1])
            except Exception:
                continue
            for n, groups in units:
                if n in spawn and t - spawn[n][0] < 0.6:
                    item = (round(t - spawn[n][0], 3), {g: [m, d.hex()] for g, (m, d) in groups.items()})
                    if not blocks[n] or blocks[n][-1][1] != item[1]:
                        blocks[n].append(item)
                elif n in names and t < 1.0:
                    tvals[n].update(read_values(groups, tnames))
                elif n in neutral and t - neutral[n]['t'] < 1.5:
                    neutral[n]['blocks'].append([round(t - neutral[n]['t'], 3), {g: [m, d.hex()] for g, (m, d) in groups.items()}])
                elif n in heroes and t < 12.0:
                    v = read_values(groups, hnames)
                    hero_state[n].update({k: v[k] for k in ('ActionState', 'ActionState2', 'StatusFlags', 'mIsTargetable',
                                                            'mIsTargetableToTeamFlags') if k in v})
        if obj == ATTACKER and 65.0 <= t <= 69.5 and pid in (740, 66, 592, 516, 779, 26, 490):
            tpl[f'attack_{pid}'].append([ch, bytes(body).hex()])
        if obj == DEAD and 654.5 <= t <= 654.8 and pid in (310, 65, 71):
            tpl[f'death_{pid}'].append([ch, bytes(body).hex()])
        if obj == VICTIM and 308.37 <= t <= 308.39 and pid in (780, 417, 440, 568):
            tpl[f'herodeath_{pid}'].append([ch, bytes(body).hex()])
        if obj == VICTIM and 322.39 <= t <= 322.40 and pid == 128:
            tpl[f'respawn_{pid}'].append([ch, bytes(body).hex()])
    minion_blocks = {}
    for kind in ('04', '05', '06'):
        nets = sorted((n for n in blocks if spawn[n][1] == kind and len(blocks[n]) >= 2), key=lambda n: spawn[n][0])
        if nets:
            n = nets[0]
            minion_blocks[kind] = dict(A=blocks[n][0][1], B=blocks[n][1][1], delay=round(blocks[n][1][0] - blocks[n][0][0], 3),
                                       wave=spawn[n][2], net=n)
    turrets = []
    for n, strs in sorted(names.items()):
        name = strs[-1]
        skin = strs[0] if len(strs) > 1 else 'SR_Fountain'
        tier = {'SR_Outer': 'outer', 'SR_Inner': 'inner', 'SR_Inhibitor': 'inhibitor', 'SR_Nexus': 'nexus'}.get(skin, 'fountain')
        side = name.split('_')[2] if name.startswith('Turret_T') else ''
        lane = LANES.get(name) or {'R': 'bot', 'C': 'mid', 'L': 'top'}.get(side, 'base')
        team = 'blue' if ('_T1_' in name or 'Order' in name) else 'red'
        v = tvals[n]
        turrets.append(dict(net=n, name=name, skin=skin, team=team, lane=lane, tier=tier, pos=POSITIONS[name],
                            hp=v.get('mMaxHP', 5000.0), armor=v.get('mArmor', 40.0), damage=v.get('mBaseAttackDamage', 152.0)))
    # the jungle: the first creation of every monster name (later creations are the replay's own respawns)
    monsters, known = [], set()
    for n, m in sorted(neutral.items(), key=lambda kv: kv[1]['t']):
        v = m['create']['value']
        name = bytes.fromhex(v['+0x24']['text']).decode('latin1')
        if name in known:
            continue
        known.add(name)
        x, y, z = struct.unpack('<fff', bytes.fromhex(v['+0x14']))
        monsters.append(dict(net=n, t=round(m['t'], 3), name=name, skin=bytes.fromhex(v['+0x4c']['text']).decode('latin1'),
                             team=int.from_bytes(bytes.fromhex(v['+0xc']), 'little'), pos=(x, z), height=y,
                             hp=m.get('hp', 1000.0), packets=m['packets'], blocks=m['blocks'], create=m['create']))
    champions = [dict(net=n, slot=h['slot'], champion=h['champion'], team='blue' if h['team_order'] == 1 else 'red',
                      pos=h.get('position'), state=hero_state.get(n, {})) for n, h in sorted(heroes.items())]
    # the templates decoded here, once (building a packet's reader tree takes about a second each): the server only
    # encodes. `spare` = the header bits the real body has set and our encoder leaves clear; `exact` = our encoding
    # of the decoded value plus those bits is the real body, byte for byte
    decoded = {}
    for key, items in tpl.items():
        pid = int(key.split('_')[1])
        if not os.path.exists(os.path.join(RES, 'codec', f'{pid}.tree.json')):
            decoded[key] = [dict(pid=pid, ch=ch, body=hx, value=None, header=0, spare=0, exact=True) for ch, hx in items]
            continue
        sc, tr = PS.Schema.load(pid), PT.Tree(pid)
        n = sc.structs[sc.root].get('header', 1)
        out = []
        for ch, hx in items:
            body = bytes.fromhex(hx)
            v = PS.decode(tr, sc, struct.pack('<HI', pid, 0) + body)
            plain = sc.encode(v) if v is not None else b''
            spare = int.from_bytes(body[:n], 'little') & ~int.from_bytes(plain[:n], 'little') if len(plain) >= n else 0
            again = (int.from_bytes(plain[:n], 'little') | spare).to_bytes(n, 'little') + plain[n:] if len(plain) >= n else plain
            out.append(dict(pid=pid, ch=ch, body=hx, value=v, header=n, spare=spare, exact=again == body))
        decoded[key] = out
    json.dump(dict(minion_blocks=minion_blocks, turrets=turrets, templates=decoded, structures=STRUCTURES,
                   attacker=ATTACKER, dead=DEAD, monsters=monsters, champions=champions, nexus=NEXUS),
              open(OUT, 'w'), indent=1)
    print('monsters:', len(monsters), [(m['name'], m['t'], round(m['hp']), len(m['packets']), len(m['blocks'])) for m in monsters])
    print('champions:', [(c['champion'], c['team'], c['pos'], c['state']) for c in champions[:3]])
    print('templates exact:', {k: [x['exact'] for x in v] for k, v in decoded.items()})
    print('minion blocks:', {k: (v['wave'], v['delay'], sorted(v['A'])) for k, v in minion_blocks.items()})
    print('turrets:', len(turrets), [(t['name'], t['tier'], t['lane'], t['hp'], t['armor'], t['damage']) for t in turrets[:4]])
    print('templates:', {k: len(v) for k, v in tpl.items()})


if __name__ == '__main__':
    main()
