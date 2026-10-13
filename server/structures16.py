"""Turrets, inhibitors and the nexus of our 16.20 world, in the live server's packet forms (events16.py recipes,
measured on data/live/4013831789).

What is measured: the 24 turrets of the start state (1200: skin SR_Outer / SR_Inner / SR_Inhibitor / SR_Nexus, map
placement name -> place from the map's own bin, tools: live turrets.json); outer turrets can be targeted from the
start, the others when the one before falls; a turret's attack = 266 (target) 827 683 906 (attack: counter, target
place, missile id, target) 972 (aim), then 938 (missile leaves) + 743 (missile object) 0.266 s later, 118 when it
lands; a falling turret = 850 {turret, killer} 266{0} 515 818 (gold) 210 (announcement) 232 (death) ...; the nexus
= 384 853 62 1129 984 (SOG_NEXUS) 550 1050 716 258, and 3.5 s later 365 {losing team} ends the match.
What is ours: reach 775 + body, one shot every 1.322 s, damage to minions as a share of their health, armor
[the usual values, 13.3's world.py]; the order: minions before champions.
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import events16    # noqa: E402

REACH, BODY = 775.0, 88.4
PERIOD, AIM, WINDUP, MISSILE = 1.322, 0.266, 0.266, 1200.0
SHARE = {4: 0.45, 5: 0.70, 6: 0.14}
HEIGHT = 50.0
STATS = {'outer': (5000.0, 15.0, 182.0), 'inner': (3600.0, 55.0, 187.0), 'inhibitor': (3300.0, 70.0, 187.0),
         'nexus': (2700.0, 70.0, 165.0), 'fountain': (9999.0, 2.0, 999.0)}
TIER = {3: 'outer', 2: 'inner', 1: 'inhibitor', 4: 'nexus', 5: 'nexus', 0: 'fountain'}
LANE = {0: 'bot', 1: 'mid', 2: 'top'}
# inhibitors and nexus: net id -> (team, lane, place) [ids: the live start state; places: the map (13.3 world_data);
# 0x4000008f chaos mid measured by the attacks aimed at it; the others paired by id order with their barracks]
OTHERS = {0x4000008a: ('order', 'bot', 'dampener', (3452.5, 1236.9)), 0x40000091: ('order', 'top', 'dampener', (1171.8, 3571.8)),
          0x4000009d: ('order', 'mid', 'dampener', (3203.0, 3208.8)), 0x400000ac: ('order', 'base', 'hq', (1551.4, 1659.6)),
          0x4000009f: ('chaos', 'bot', 'dampener', (13604.6, 11316.0)), 0x4000009e: ('chaos', 'top', 'dampener', (11261.7, 13676.6)),
          0x4000008f: ('chaos', 'mid', 'dampener', (11598.1, 11667.8)), 0x400000a8: ('chaos', 'base', 'hq', (13142.7, 12964.9))}


class Structure:
    def __init__(self, net, team, lane, tier, pos, name=''):
        self.net, self.team, self.lane, self.tier, self.xy, self.name = net, team, lane, tier, tuple(pos), name
        hp, self.armor, self.damage = STATS.get(tier, (4000.0 if tier == 'dampener' else 5500.0, 20.0, 0.0))
        if tier == 'dampener':
            hp = 4000.0
        elif tier == 'hq':
            hp = 5500.0
        self.hp = self.max_hp = hp
        self.alive = True
        self.open = tier in ('outer',)          # [measured] only the outer turrets can be targeted at the start
        self.target = None
        self.next_attack = 0.0
        self.attacks = 0
        self.is_structure = True
        self.kind = 0

    def place(self):
        return self.xy


class Structures:
    def __init__(self, world, live):
        self.w = world
        self.ev = events16.Events(live)
        self.all = {}
        for d in json.load(open(os.path.join(live, 'turrets.json'))):
            tier = TIER[d['p']]
            self.all[d['net']] = Structure(d['net'], d['team'], LANE.get(d['lane'], 'mid') if tier not in ('nexus', 'fountain') else 'base',
                                           tier, d['pos'], d['name'])
        for net, (team, lane, tier, pos) in OTHERS.items():
            self.all[net] = Structure(net, team, lane, tier, pos)
        self.last_think = 0.0
        self.over = None

    # ------------------------------------------------------------------ helpers
    def send_recipe(self, t, name, roles, change=None, skip=()):
        for dt, ch, pid, net, body in self.ev.make(name, roles, change, skip):
            if dt <= 0.002:
                self.w.out.append((ch, pid, net, body))
            else:
                self.w.push(t + dt, lambda t2, it=(ch, pid, net, body): self.w.out.append(it))

    def near(self, team, here, reach):
        """the nearest enemy structure that can be attacked within reach of here"""
        best = None
        for s in self.all.values():
            if s.alive and s.open and s.team != team:
                d = math.dist(here, s.xy) - BODY
                if d <= reach and (best is None or d < best[0]):
                    best = (d, s)
        return best[1] if best else None

    # ------------------------------------------------------------------ turrets attack
    def tick(self, t):
        if t - self.last_think < 0.1 or self.over:
            return
        self.last_think = t
        for tu in self.all.values():
            if not tu.alive or tu.tier in ('dampener', 'hq'):
                continue
            tgt = self.w.unit(tu.target) if tu.target else None
            if tgt is not None and (not tgt.alive or math.dist(tu.xy, tgt.place()) > REACH + BODY + 60):
                self.stop(tu)
                tgt = None
            if tgt is None:
                tgt = self.choose(tu)
                if tgt is None:
                    continue
                tu.target = tgt.net
                tu.first = True
                tu.next_attack = max(tu.next_attack, t + AIM)
                continue
            if t >= tu.next_attack:
                self.attack(t, tu, tgt)

    def choose(self, tu):
        reach = (1200.0 if tu.tier == 'fountain' else REACH) + BODY
        best = None
        for m in self.w.units.values():
            if m.alive and m.team != tu.team and tu.tier != 'fountain':
                d = math.dist(tu.xy, m.xy)
                if d <= reach and (best is None or d < best[0]):
                    best = (d, m)
        if best is None:
            for h in self.w.champions():
                if h.alive and h.team != tu.team:
                    d = math.dist(tu.xy, h.place())
                    if d <= reach and (best is None or d < best[0]):
                        best = (d, h)
        return best[1] if best else None

    def attack(self, t, tu, tgt):
        tu.attacks += 1
        missile = self.w.new_net()
        there = tgt.place()
        pos = struct.pack('<fff', there[0], HEIGHT, there[1]).hex()
        roles = {'T': tu.net, 'X': tgt.net, 'M': missile}

        def a906(v):
            v['+0x10']['+0x8'] = struct.pack('<I', 0x100 + tu.attacks).hex()
            v['+0x10']['+0x10'] = pos
            if '+0x48' in v:
                v['+0x48'] = struct.pack('<ff', tu.xy[0], tu.xy[1]).hex()
            return v
        change = {906: a906, 972: {'+0x14': pos}}
        # every attack as the first one (266 827 683 906 972): 51, the real server's form of the next ones, is not learnt
        self.send_recipe(t, 'turret_first_attack', roles, change, skip=() if getattr(tu, 'first', True) else (266, 827))
        tu.first = False
        tu.next_attack = (tu.next_attack if t - tu.next_attack < 0.2 else t) + PERIOD
        self.w.push(t + WINDUP, lambda t2: self.missile(t2, tu, tgt, missile))

    def missile(self, t, tu, tgt, missile):
        if not tu.alive:
            return
        self.send_recipe(t, 'turret_missile', {'T': tu.net, 'M': missile})
        flight = max(0.0, math.dist(tu.xy, tgt.place()) - BODY) / MISSILE
        self.w.push(t + flight, lambda t2: self.lands(t2, tu, tgt, missile))

    def lands(self, t, tu, tgt, missile):
        self.w.out.append((1, 118, missile, self.ev.schema(118).encode({'+0x10': '01'})))
        if not tgt.alive:
            return
        if getattr(tgt, 'is_hero', False):
            self.w.hit(t, _Src(tu.net, tu.damage), tgt, share=1.0)
        else:
            damage = SHARE.get(getattr(tgt, 'kind', 4), 0.45) * tgt.max_hp
            self.w.hit(t, _Src(tu.net, damage), tgt, share=1.0)

    def stop(self, tu):
        tu.target = None
        tu.first = True
        self.w.out.append((1, 266, tu.net, self.ev.schema(266).encode({'+0x10': '00000000'})))

    # ------------------------------------------------------------------ structures take damage and fall
    def hit(self, t, source, s, damage):
        if not s.alive or not s.open:
            return
        damage = damage * 100.0 / (100.0 + s.armor)
        s.hp = max(0.0, s.hp - damage)
        cls = 'AITurretCommon' if s.tier not in ('dampener', 'hq') else 'BarracksDampenerCommon'
        self.w.repl.append((s.net, {'mHP': s.hp}, cls))
        if s.hp <= 0:
            self.falls(t, s, source)

    def falls(self, t, s, source):
        s.alive = s.open = False
        killer = getattr(source, 'net', 0)
        if s.tier == 'hq':
            return self.nexus_falls(t, s, killer)
        if s.tier == 'dampener':
            self.w.repl.append((s.net, {'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3}, 'BarracksDampenerCommon'))
        else:
            self.send_recipe(t, 'turret_falls', {'T': s.net, 'K': killer},
                             change={232: lambda v: v.update({'+0x50': struct.pack('<I', killer).hex()}) or v},
                             skip=(938, 904, 584, 635, 683, 827, 262, 515, 88, 78))
            self.w.repl.append((s.net, {'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3}, 'AITurretCommon'))
        for o in self.all.values():
            if o.target == s.net:
                o.target = None
        # the next structure of the lane can be attacked
        order = ['outer', 'inner', 'inhibitor', 'dampener']
        if s.tier in order[:-1]:
            want = order[order.index(s.tier) + 1]
            for o in self.all.values():
                if o.team == s.team and o.lane == s.lane and o.tier == want and o.alive and not o.open:
                    o.open = True
                    cls = 'AITurretCommon' if want != 'dampener' else 'BarracksDampenerCommon'
                    self.w.repl.append((o.net, {'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4}, cls))
        if s.tier == 'dampener':
            for o in self.all.values():
                if o.team == s.team and o.tier == 'nexus' and o.alive and not o.open:
                    o.open = True
                    self.w.repl.append((o.net, {'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4}, 'AITurretCommon'))
        if s.tier == 'nexus' and not any(o.alive for o in self.all.values() if o.team == s.team and o.tier == 'nexus'):
            for o in self.all.values():
                if o.team == s.team and o.tier == 'hq' and o.alive:
                    o.open = True
                    self.w.repl.append((o.net, {'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4}, 'BarracksDampenerCommon'))
        self.w.events.append(('structure_falls', s.net, s.team, s.tier, killer))

    def nexus_falls(self, t, s, killer):
        self.over = s.team
        player = self.w.player.net if getattr(self.w, 'player', None) else 0
        cam = struct.pack('<fff', s.xy[0], 91.0, s.xy[1]).hex()
        tm = struct.pack('<f', t).hex()
        self.send_recipe(t, 'nexus_falls', {'N': s.net, 'K': killer, 'P': player},
                         change={258: {'+0x18': cam}, 1050: {'+0x14': tm, '+0x18': tm}})
        lost = 'c8' if s.team == 'chaos' else '64'
        self.w.push(t + 3.5, lambda t2: self.send_recipe(t2, 'match_ends', {}, change={365: {'+0x10': lost}}))
        self.w.events.append(('game_over', s.team, killer))


class _Src:
    """an attacker for World16.hit: its net id and the damage it does"""
    def __init__(self, net, damage):
        self.net, self.damage = net, damage
