"""Our server's own Summoner's Rift on 16.20 (the match without the replay): lane minion waves.

What is copied from Riot's server is measured on the 16.20 replay (tools/world_data16.py -> data/exe1620/world16.json;
server/x_life.py for the order of packets about one unit):
  - a wave every 30.03 s from 30.06 s, from each of the 6 barracks; its minions 0.802 s apart: 3 melee (kind 4),
    a cannon (6) on every third wave, 3 casters (5)
  - a new minion: the spawn packet (439); 0.033 s later it enters the player's sight: 723 (visible to team 1 / 2:
    the replay's value is the minion's own team; ours is always the player's team, there is no fog of war yet), 239
    (an empty packet), 684 (health, full health and the way out of its barracks as a waypoint entry with the
    movement counter) and its replicated values (what it may do, health); 0.234 s after the spawn the second
    block (damage, range, move speed) - both blocks as the replay has them, by name
    [measured: with 439 + replication + moves alone the client shows no minion at all; with 723 + 239 + 684 it does]
  - the client walks a new minion out of its barracks itself; the server's first move comes 3-4.4 s later, at speed
    350 (cannon 452), along the lane: the walk of the replay's first minion of that barracks to where it met the
    enemy, then the enemy's walk backwards to the enemy base
Fights (rules ours and simple, packet forms the replay's; only when world16.json has the templates):
  - a minion with an enemy minion of its lane within its reach stands (a one-point move) and attacks: 447 (target),
    390 (attack: counter, slot 0x40 / 0x41, target place, the attack's own net id, target), the damage after the
    windup (and a missile's flight) as the replay's two 150 (the amount taken, then the full amount), the target's
    health in the replication; at zero 1112 (death, killer), 515 to those attacking it, 1090 four seconds later
  - reach, time between attacks, windup, missile speed and the share of damage taken are the usual values of these
    units [approximations, not measured]

  world16.py sim [seconds]     run the world alone and read every packet back through the client's own readers
"""
import bisect
import collections
import copy
import heapq
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['BA_PATCH'] = '1620'
import lol_packets      # noqa: E402
import repl16           # noqa: E402
import roles16 as R     # noqa: E402
import waypoints        # noqa: E402

RES = os.path.join(HERE, '..', 'data', 'exe1620')
NET_BASE = 0x40002000         # our units' net ids (the start state uses up to about 0x400002b3)
THINK = 0.25                  # how often a minion looks around (LeagueSandbox's lane minion does the same)
ACQUIRE = 700.0               # an enemy minion this near is gone for [approximation]
MOVE_COUNTER_RATE = 913.0     # the movement packet's counter grows about this much a second in the replay
BODY = 48.0                   # a lane minion's body [approximation]
# per kind: time between attacks, windup, missile speed (0 = melee), share of the damage a minion takes [approximations]
FIGHT = {4: dict(period=1.337, windup=0.30, missile=0.0, share=0.845),
         5: dict(period=1.60, windup=0.40, missile=650.0, share=0.51),
         6: dict(period=1.00, windup=0.35, missile=1200.0, share=0.80)}
CORPSE = 4.0                  # death -> the unit is removed (replay: 69.66 -> 73.67)
GOLD = {4: 21.0, 5: 14.0, 6: 60.0}   # to a champion that kills the minion [the usual amounts; live: 20 / 21 for melee]
XP = {4: 62.0, 5: 31.0, 6: 93.0}     # experience of a minion's death [measured live: melee 62, caster 31; cannon ours]


def to_cell(p):
    return (int(round((p[0] - waypoints.CENTER[0]) / waypoints.CELL)), int(round((p[1] - waypoints.CENTER[1]) / waypoints.CELL)))


class Path:
    """a polyline walked at constant speed"""
    def __init__(self, points):
        self.p = [tuple(x) for x in points]
        self.cum = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))

    def at(self, s):
        s = min(max(s, 0.0), self.cum[-1])
        i = min(bisect.bisect_right(self.cum, s) - 1, len(self.p) - 2)
        a, b = self.p[i], self.p[i + 1]
        d = self.cum[i + 1] - self.cum[i]
        k = (s - self.cum[i]) / d if d else 0.0
        return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)

    def ahead(self, s, count=3):
        """the points still to come after distance s, and the lane distance of the last of them"""
        i = bisect.bisect_right(self.cum, s)
        pts = self.p[i:i + count]
        return pts, (self.cum[i + len(pts) - 1] if pts else self.cum[-1])


class Minion:
    def __init__(self, net, team, lane, kind, wave, path, spawn_t, first_move, values):
        self.net, self.team, self.lane, self.kind, self.wave, self.path = net, team, lane, kind, wave, path
        self.spawn_t, self.first_move = spawn_t, first_move
        self.hp = self.max_hp = float(values.get('mHP', 400.0))
        self.damage = float(values.get('mBaseAttackDamage', 12.0))
        self.range = float(values.get('mAttackRange', 110.0))
        self.speed = float(values.get('mMoveSpeed', 350.0))
        self.s = 0.0                 # distance walked along the lane
        self.moving = False
        self.alive = True
        self.target = None
        self.next_attack = 0.0
        self.attack_net = None       # the net id its attacks carry: one per attacker, as in the replay
        self.attacks = 0
        self.xy = self.path.at(0.0)  # where it is now
        self.seg = None              # a straight walk off the lane: the point it goes to
        self.after = None            # ... and the lane distance it joins the lane at when it gets there
        self.sent_until = float('inf')   # lane distance of the last point the client was given
        self.started = False         # the server's first move has gone out
        self.spot = None             # its own place next to its target

    def place(self):
        return self.xy


class World16:
    def __init__(self, live=None):
        """live: data/live/<gameId> -> the real server's forms of a LIVE match (tools/live_world16.py): a new minion is
        the 239 container holding its 439 spawn, with 684 and the replication blocks in the same tick (no 723: that
        is the replay's spectator form). The barracks and lanes stay the replay's (both teams whole; a live player
        sees the other team's minions only in sight)."""
        import pkt_schema as PS
        d = self.data = json.load(open(os.path.join(RES, 'world16.json')))
        self.live = None
        if live:
            L = self.live = json.load(open(os.path.join(live, 'world16.json')))
            d['waves'] = L['waves']
            for k, sp in L['spawn'].items():
                d['spawn'][k] = dict(d['spawn'].get(k, {}), **sp)
            for b, e in L['enter'].items():
                if b in d['enter'] and all(v.get('delay', 1.0) < 0.05 for v in e['kinds'].values()):
                    d['enter'][b] = dict(d['enter'][b], prefix=e['prefix'], mark=e['mark'],
                                         kinds=dict(d['enter'][b]['kinds'], **e['kinds']))
            for k, v in L['templates'].items():
                if 'raw' not in v:
                    d.setdefault('templates', {})[k] = v
        self.sc = {}
        for pid in (R.MINION_SPAWN, R.MOVE, R.HERO_ATTACK, R.ATTACK_972, R.DAMAGE, R.TARGET, R.STOP_ATTACK, R.DEATH, R.DELETE,
                    R.VISIBILITY_723, R.ENTER_DATA, R.GOLD, R.ENTER_239):
            try:
                self.sc[pid] = PS.Schema.load(pid)
            except Exception:
                pass                 # a format not learnt yet: that packet is left out (see `missing`)
        self.missing = set()
        self.templates = d.get('templates', {})
        self.barracks = {int(b, 16): v for b, v in d['barracks'].items()}
        # a minion's whole way: out of its barracks (the replay's first point), then the lane
        self.paths = {b: Path([d['enter'][f'{b:x}']['path'][0]] + v['lane_path']) for b, v in self.barracks.items()}
        self.player_team = 1         # 723's value for "the order team sees it"
        self.units = {}
        self.next_net = NET_BASE
        self.wave = 0
        self.later = []              # (time, order, callable)
        self.order = 0
        self.move_counter = 0
        self.repl_counter = 3_000_000
        self.last_think = 0.0
        self.last_t = 0.0
        self.out = []
        self.moves = []              # waypoint entries collected in a tick
        self.repl = []               # (net, values, class) collected in a tick
        self.stats = collections.Counter()
        self.events = []             # what happened to the player's champions: ('gold', net, amount)
        self.structs = None          # turrets / inhibitors / nexus (structures16.py), with a live recording
        self.heroes = {}             # champions in the world: net id -> object with .net .team .alive .place() .take()
        self.player = None
        if live:
            import structures16
            self.structs = structures16.Structures(self, live)

    # ------------------------------------------------------------------ packets
    def send(self, pid, net, values):
        sc = self.sc.get(pid)
        if sc is None:
            self.missing.add(pid)
            return
        self.out.append((R.CHANNEL.get(pid, 1), pid, net, sc.encode(values)))
        self.stats[pid] += 1

    def push(self, at, fn):
        self.order += 1
        heapq.heappush(self.later, (at, self.order, fn))

    def new_net(self):
        self.next_net += 1
        return self.next_net

    def flush(self, t):
        for i in range(0, len(self.moves), 16):
            group = self.moves[i:i + 16]
            self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
            self.send(R.MOVE, 0, {'+0x10': struct.pack('<H', len(group)).hex(), '+0x18': {'text': b''.join(group).hex()},
                                  '+0x28': struct.pack('<I', self.move_counter).hex()})
        self.moves = []
        for i in range(0, len(self.repl), 12):
            group = self.repl[i:i + 12]
            self.repl_counter += 1
            self.out.append((2, R.REPLICATION, 0, repl16.packet(group, game_time=t, counter=self.repl_counter)))
            self.stats[R.REPLICATION] += 1
        self.repl = []

    def move(self, m, points):
        self.moves.append(lol_packets.waypoint_entry(m.net, [to_cell(p) for p in points], m.speed, flags=0))

    # ------------------------------------------------------------------ waves
    def kinds_of(self, wave):
        k = self.data['waves']['kinds'].get(str(wave))
        return k or ([4, 4, 4, 6, 5, 5, 5] if wave % 3 == 0 else [4, 4, 4, 5, 5, 5])

    def schedule_wave(self, wave):
        w = self.data['waves']
        t0 = w['first'] + (wave - 1) * w['period']
        for i, kind in enumerate(self.kinds_of(wave)):
            for b in self.barracks:
                self.push(t0 + i * w['between_minions'], lambda t, b=b, kind=kind, wave=wave: self.spawn(t, b, kind, wave))

    def spawn(self, t, b, kind, wave):
        tpl = self.data['spawn'].get(str(kind)) or self.data['spawn']['4']
        bar = self.barracks[b]
        values = {}
        for blk in tpl['blocks']:
            values.update(blk['values'])
        net = self.new_net()
        m = Minion(net, bar['team'], bar['lane'], kind, wave, self.paths[b], t, t + bar['first_move_delay'], values)
        m.speed = float(tpl['speed'])
        # the client walks the way out by itself: our first move must come before it reaches the end of that way
        way = self.data['enter'][f'{b:x}']['path']
        m.first_move = min(m.first_move, t + math.dist(way[0], way[-1]) / m.speed - 0.4)
        self.units[net] = m
        f = dict(tpl['fields'])
        f['+0x14'] = struct.pack('<I', b).hex()
        f['+0x18'] = f'{kind:02x}'
        f['+0x1c'] = struct.pack('<I', net).hex()
        f['+0x20'] = f'{wave & 0xff:02x}'
        f['+0x24'] = struct.pack('<f', t).hex()
        en = self.data['enter'][f'{b:x}']
        ek = en['kinds'].get(str(kind)) or en['kinds']['4']
        if self.live is not None:
            # live form: 239{439} + 684 in the spawn's own tick, the replication blocks at their measured delays
            import forms16
            spawn_body = self.sc[R.MINION_SPAWN].encode(f)
            self.send(forms16.CONTAINER, net, forms16.pack([(R.MINION_SPAWN, net, spawn_body)]))
            self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
            entry = lol_packets.waypoint_entry(net, [to_cell(q) for q in en['path']], m.speed, flags=en['flags'])
            blob = bytes.fromhex(en['prefix']) + bytes([en['mark']]) + struct.pack('<I', self.move_counter) + entry
            self.send(R.ENTER_DATA, net, {'+0x10': {'text': struct.pack('<fff', m.hp, 0.0, m.max_hp).hex()}, '+0x20': {'text': blob.hex()}})
            m.moving = True
            for blk in tpl['blocks']:
                if blk['delay'] <= 0.001:
                    self.repl.append((net, blk['values'], 'lane_minion'))
                elif blk['delay'] < 1.0:
                    self.push(t + blk['delay'], lambda t2, vals=blk['values'], net=net: self.repl.append((net, vals, 'lane_minion')))
            self.push(m.first_move, lambda t2, m=m: self.walk(m))
            return
        self.send(R.MINION_SPAWN, net, f)

        def enters(t2):
            self.send(R.VISIBILITY_723, net, {'+0x10': f'{self.player_team:02x}'})
            self.out.append((1, R.ENTER_239, net, bytes.fromhex(self.data['raw']['239'])))
            self.move_counter = max(self.move_counter + 1, 2000 + int(t2 * MOVE_COUNTER_RATE))
            entry = lol_packets.waypoint_entry(net, [to_cell(q) for q in en['path']], m.speed, flags=en['flags'])
            blob = bytes.fromhex(en['prefix']) + bytes([en['mark']]) + struct.pack('<I', self.move_counter) + entry
            self.send(R.ENTER_DATA, net, {'+0x10': {'text': struct.pack('<fff', m.hp, 0.0, m.max_hp).hex()}, '+0x20': {'text': blob.hex()}})
        self.push(t + 0.033, enters)
        m.moving = True              # the client walks it out of the barracks by itself (684's path)
        for blk in tpl['blocks']:
            self.push(t + max(0.034, min(blk['delay'], 0.3)), lambda t2, vals=blk['values'], net=net: self.repl.append((net, vals, 'lane_minion')))
        self.push(m.first_move, lambda t2, m=m: self.walk(m))

    def walk(self, m):
        """Along the lane from where the minion is. The client is given the next points only (the real server sends
        two-point moves every 3-6 s); tick() calls this again before the client reaches the last one - a minion left
        at the end of its points stands there in the client while it walks on here, and the next packet about it
        shows as a jump (the user saw exactly that: the first stops, the others walk into it, then they teleport)."""
        if not m.alive:
            return
        pts, until = m.path.ahead(m.s)
        m.seg, m.after, m.started = None, None, True
        if not pts:
            m.moving = False
            return
        m.moving, m.sent_until = True, until
        self.move(m, [m.xy] + pts)

    def rejoin(self, m):
        """back to the lane after a fight: straight to a lane point a little ahead, then on along the lane"""
        s2 = min(m.s + 150.0, m.path.cum[-1])
        p = m.path.at(s2)
        pts, until = m.path.ahead(s2, 2)
        m.seg, m.after, m.moving, m.sent_until = p, s2, True, (until if pts else s2)
        self.move(m, [m.xy, p] + pts)

    def go(self, m, where):
        """a straight walk to a point off the lane (its place in a fight)"""
        m.seg, m.after, m.moving = where, None, True
        self.move(m, [m.xy, where])

    def stand(self, m):
        m.moving, m.seg, m.after = False, None, None
        self.move(m, [m.xy])

    # ------------------------------------------------------------------ fights
    def reach(self, m):
        return m.range + 2 * BODY

    def free_spot(self, m, tgt, others):
        """A place for m to fight tgt from that no other unit stands on or walks to: on a circle around the target at
        m's reach, starting on m's side and stepping to both sides (LeagueSandbox / our 13.3 world did the same:
        without it every minion of a wave stops on the same point of the lane)."""
        dx, dz = m.xy[0] - tgt.xy[0], m.xy[1] - tgt.xy[1]
        d = math.hypot(dx, dz) or 1.0
        r = min(d, m.range + BODY + (88.0 if getattr(tgt, 'is_structure', False) else 0.0))
        base = math.atan2(dz, dx)
        step = 2 * math.asin(min(1.0, BODY / max(r, BODY)))
        for k in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5):
            a = base + k * step
            p = (tgt.xy[0] + r * math.cos(a), tgt.xy[1] + r * math.sin(a))
            if all(math.dist(p, (o.spot if (o.spot and o.moving) else o.xy)) > 1.7 * BODY for o in others if o is not m):
                return p
        return (tgt.xy[0] + r * math.cos(base), tgt.xy[1] + r * math.sin(base))

    def think(self, t):
        by_lane = collections.defaultdict(list)
        for m in self.units.values():
            if m.alive and m.started:
                by_lane[m.lane].append(m)
        for lane, ms in by_lane.items():
            for m in ms:
                here = m.xy
                tgt = self.units.get(m.target) if m.target else None
                if tgt is None and m.target:
                    tgt = self.unit(m.target)
                if tgt is None or not tgt.alive or math.dist(here, tgt.place()) > ACQUIRE + 200:
                    near = [(math.dist(here, o.xy), o) for o in ms if o.team != m.team]
                    near = [x for x in near if x[0] <= ACQUIRE]
                    tgt = min(near, key=lambda x: x[0])[1] if near else None
                    if tgt is None and self.structs is not None:
                        tgt = self.structs.near(m.team, here, ACQUIRE)
                    if tgt is None:
                        champs = [(math.dist(here, h.place()), h) for h in self.champions() if h.alive and h.team != m.team]
                        champs = [x for x in champs if x[0] <= ACQUIRE * 0.7]
                        tgt = min(champs, key=lambda x: x[0])[1] if champs else None
                    if tgt is not None and m.target != tgt.net:
                        self.send(R.TARGET, m.net, self.field(R.TARGET, {'+0x10': struct.pack('<I', tgt.net).hex()}))
                    m.target, m.spot = (tgt.net if tgt else None), None
                if tgt is None:
                    if not m.moving and m.s < m.path.cum[-1] - 1:
                        self.rejoin(m)
                    continue
                d = math.dist(here, tgt.place()) - (88.0 if getattr(tgt, 'is_structure', False) else 0.0)
                if m.spot is None or (not m.moving and d > self.reach(m)):
                    # a place of its own next to the target (again when it stands and the target has moved away)
                    m.spot = self.free_spot(m, tgt, ms)
                    if math.dist(here, m.spot) > 25.0:
                        self.go(m, m.spot)
                    elif m.moving:
                        self.stand(m)
                    continue
                if not m.moving and d <= self.reach(m) and t >= m.next_attack and self.can_fight():
                    self.attack(t, m, tgt)

    def field(self, pid, changes):
        v = copy.deepcopy(self.templates.get(str(pid), {}))
        v.update(changes)
        return v

    def can_fight(self):
        a = self.templates.get(str(R.HERO_ATTACK))
        return bool(a) and isinstance(a.get('+0x10'), dict) and '+0x8' in a['+0x10']

    def attack(self, t, m, tgt):
        """The attack packet is 906 (the one the replay uses for champions): its inner struct (counter, slot, target
        place, the attack's own net id, target) is the one a minion's 390 carries too, and 390's tail is not learnt."""
        f = FIGHT[m.kind]
        m.next_attack = t + f['period']
        m.attacks += 1
        if m.attack_net is None:
            m.attack_net = self.new_net()
        here, there = m.place(), tgt.place()
        v = copy.deepcopy(self.templates[str(R.HERO_ATTACK)])
        v['+0x10'].update({'+0x8': struct.pack('<I', m.attacks).hex(), '+0xd': '40' if m.attacks % 2 else '41',
                           '+0x10': struct.pack('<fff', there[0], 50.0, there[1]).hex(),
                           '+0x1c': struct.pack('<I', m.attack_net).hex(), '+0x20': struct.pack('<I', tgt.net).hex()})
        v['+0x48'] = struct.pack('<ff', here[0], here[1]).hex()
        self.send(R.HERO_ATTACK, m.net, v)
        self.send(R.ATTACK_972, m.net, self.field(R.ATTACK_972, {'+0x10': struct.pack('<I', tgt.net).hex(),
                                                                '+0x14': struct.pack('<fff', there[0], 50.0, there[1]).hex(), '+0x20': '02'}))
        delay = f['windup'] + (math.dist(here, there) / f['missile'] if f['missile'] else 0.0)
        self.push(t + delay, lambda t2, m=m, tgt=tgt: self.hit(t2, m, tgt))

    def hit(self, t, m, tgt, share=None):
        """m's attack lands on tgt (m: a minion of ours, or anything with .net and .damage - the player's champion,
        a turret); tgt: a minion, a structure, a champion"""
        if not tgt.alive:
            return
        if getattr(tgt, 'is_structure', False):
            self.structs.hit(t, m, tgt, m.damage * (share if share is not None else 1.0))
            return
        if getattr(tgt, 'is_hero', False):
            tgt.take(t, m, m.damage * (share if share is not None else FIGHT.get(getattr(m, 'kind', 4), FIGHT[4])['share']), self)
            return
        taken = m.damage * (share if share is not None else FIGHT[m.kind]['share'])
        base = {'+0x14': struct.pack('<I', tgt.net).hex(), '+0x1c': struct.pack('<I', m.net).hex()}
        self.send(R.DAMAGE, tgt.net, self.field(R.DAMAGE, dict(base, **{'+0x10': struct.pack('<f', taken).hex(), '+0x19': '00',
                                                                         '+0x2c': '00000000'})))
        self.send(R.DAMAGE, tgt.net, self.field(R.DAMAGE, dict(base, **{'+0x10': struct.pack('<f', m.damage).hex(), '+0x19': '01'})))
        tgt.hp -= taken
        if tgt.hp > 0:
            self.repl.append((tgt.net, {'mHP': tgt.hp}, 'lane_minion'))
            return
        tgt.alive = False
        here = tgt.place()
        v = copy.deepcopy(self.templates[str(R.DEATH)])
        v['+0x10']['+0x20'] = struct.pack('<fff', here[0], 50.0, here[1]).hex()
        v['+0x50'] = struct.pack('<I', m.net).hex()
        self.send(R.DEATH, tgt.net, v)
        self.repl.append((tgt.net, {'mHP': 0.0}, 'lane_minion'))
        for o in self.units.values():
            if o.alive and o.target == tgt.net:
                o.target = None
                if o.attack_net:
                    self.send(R.STOP_ATTACK, o.net, self.field(R.STOP_ATTACK, {'+0x14': struct.pack('<I', o.attack_net).hex()}))
        self.push(t + CORPSE, lambda t2, net=tgt.net: self.remove(net))
        self.stats['deaths'] += 1
        if getattr(m, 'is_hero', False):          # the gold goes to the champion that made the kill (818)
            amount = GOLD.get(tgt.kind, 20.0)
            self.send(R.GOLD, m.net, self.field(R.GOLD, {'+0x14': struct.pack('<f', amount).hex(),
                                                         '+0x18': struct.pack('<I', m.net).hex(),
                                                         '+0x1c': struct.pack('<I', tgt.net).hex()}))
            self.events.append(('gold', m.net, amount))
        # the experience goes to the enemy champions near the dying minion, shared [measured live: a melee minion gives
        # 62 to a champion alone, a caster 31; 1400 range and the share: the usual rule]
        near = [h for h in self.champions() if h.alive and h.team != tgt.team and math.dist(h.place(), here) <= 1400.0]
        for h in near:
            h.gain_xp(t, XP.get(tgt.kind, 30.0) / len(near), self)

    def unit(self, net):
        """any unit of the world by net id: a minion, a structure, a champion"""
        u = self.units.get(net)
        if u is None and self.structs is not None:
            u = self.structs.all.get(net)
        return u if u is not None else self.heroes.get(net)

    def champions(self):
        return list(self.heroes.values())

    def remove(self, net):
        self.units.pop(net, None)
        self.send(R.DELETE, net, self.field(R.DELETE, {'+0x10': struct.pack('<I', net).hex()}))

    # ------------------------------------------------------------------ the clock
    def tick(self, t):
        """everything that happens up to game time t -> [(channel, packet id, net id, body)]"""
        self.out = []
        w = self.data['waves']
        while w['first'] + self.wave * w['period'] - 1.0 <= t:
            self.wave += 1
            self.schedule_wave(self.wave)
        while self.later and self.later[0][0] <= t:
            at, _, fn = heapq.heappop(self.later)
            fn(at)
        dt = max(0.0, t - self.last_t)
        self.last_t = t
        for m in list(self.units.values()):
            if not (m.alive and m.moving):
                continue
            step = m.speed * dt
            if m.seg is not None:                 # a straight walk off the lane
                d = math.dist(m.xy, m.seg)
                if d <= step:
                    m.xy = m.seg
                    m.seg = None
                    if m.after is None:
                        m.moving = False
                    else:
                        m.s, m.after = m.after, None
                else:
                    m.xy = (m.xy[0] + (m.seg[0] - m.xy[0]) * step / d, m.xy[1] + (m.seg[1] - m.xy[1]) * step / d)
                continue
            m.s += step
            if m.s >= m.path.cum[-1]:
                m.s, m.moving = m.path.cum[-1], False
            m.xy = m.path.at(m.s)
            # the client's points are about to run out: give it the next ones (0.7 s ahead of its last point)
            if m.started and m.moving and m.s > m.sent_until - 0.7 * m.speed and m.sent_until < m.path.cum[-1] - 1:
                self.walk(m)
        if self.structs is not None:
            self.structs.tick(t)
        if t - self.last_think >= THINK:
            self.last_think = t
            self.think(t)
        self.flush(t)
        return self.out


if __name__ == '__main__':
    import pkt_schema as PS
    import pkt_tree as PT
    from emu_backend import P
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
    W = World16()
    t, sent, bad = 0.0, collections.Counter(), collections.Counter()
    trees = {}
    while t < secs:
        for ch, pid, net, body in W.tick(t):
            sent[pid] += 1
            if sent[pid] <= 40 or sent[pid] % 25 == 0:          # read back a sample of every kind
                sc = W.sc.get(pid) or PS.Schema.load(pid)
                T = trees.setdefault(pid, PT.Tree(pid))
                if PS.decode(T, sc, P.wire(pid, net, body)) is None:
                    bad[pid] += 1
        t += 1 / 30
    alive = [m for m in W.units.values() if m.alive]
    print(f'{secs:.0f} s: sent {dict(sent)}; not read by the client\'s reader: {dict(bad) or "none"}')
    print(f'units alive {len(alive)}, deaths {W.stats["deaths"]}, formats missing: {sorted(W.missing) or "none"}')
    for lane in ('top', 'mid', 'bot'):
        ms = [m for m in alive if m.lane == lane]
        print(f'  {lane}: order {sum(1 for m in ms if m.team == "order")} chaos {sum(1 for m in ms if m.team == "chaos")}',
              [tuple(round(c) for c in m.place()) for m in ms[:3]])
