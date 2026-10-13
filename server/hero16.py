"""The player's own champion on 16.20, moved by our server: the client's order (packet 1032, decoded with the
format learnt from the client's writer, c2s16.py) is answered with a movement packet of ours (61, written with the
format learnt from the client's reader, pkt_schema).

Measured on the 16.20 replay (x_buf.py 61): the movement packet's buffer holds 13.3's waypoint entries unchanged
(waypoints.py); the real server sends a champion's entry with flags 0, its current move speed, the path's points
from where the unit stands; object +0x10 = how many units, +0x28 = a counter that only grows (about 913 a second);
channel 2.

  hero16.py test       an order decoded and our answer read back by the client's own reader (no game needed)
"""
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['BA_PATCH'] = '1620'
import netid16         # noqa: E402
import waypoints       # noqa: E402
import lol_packets     # noqa: E402

MOVE, ORDER = 61, 1032
SKILL_UP_REQUEST, SKILL_LEVEL = 544, 810
MOVE_CHANNEL = 2
COUNTER_RATE = 913.0
RES = os.path.join(HERE, '..', 'data', 'exe1620')


def to_cell(p):
    return (int(round((p[0] - waypoints.CENTER[0]) / waypoints.CELL)), int(round((p[1] - waypoints.CENTER[1]) / waypoints.CELL)))


class Hero:
    def __init__(self, net, speed=335.0, place=None, values=None):
        import pkt_schema as PS
        import c2s16
        self.net, self.speed = net, speed
        self.sc = PS.Schema.load(MOVE)
        self.c2s = c2s16
        self.order_spec = json.load(open(os.path.join(RES, 'codec', f'c2s_{ORDER}.json')))
        for f in self.order_spec['fields']:
            f['modes'] = {int(m): d for m, d in f['modes'].items()}
        self.a = self.b = place or self.start_place()
        self.t0 = 0.0
        self.counter = 2000
        # the champion's replicated values as the real server set them in the replay's first 5 s (hero_start.json),
        # with the homeguard speed taken back to the walking speed we move it at
        self.values = dict(values) if values is not None else json.load(open(os.path.join(RES, 'hero_start.json')))[f'{net:x}']
        self.values['mMoveSpeed'] = speed
        self.is_hero = True
        self.damage = float(self.values.get('mBaseAttackDamage', 50.0)) + float(self.values.get('mFlatPhysicalDamageMod', 0.0))
        self.range = float(self.values.get('mAttackRange', 550.0))
        self.target = None           # net id of the unit it was told to attack
        self.next_attack = 0.0
        self.attacks = 0
        self.attack_net = None
        self.last_path = -1.0
        self.gold = float(self.values.get('mGold', 0.0))
        self.levels = [0, 0, 0, 0]
        self.points = 1
        self.repl_counter = 5_000_000
        self.skill = json.load(open(os.path.join(RES, 'codec', 'c2s_544_slot.json')))
        self.team = 'order'
        self.alive = True
        self.home = self.a
        self.max_hp = float(self.values.get('mMaxHP', 0.0) or self.values.get('mHP', 600.0) or 600.0)
        self.hp = float(self.values.get('mHP', self.max_hp) or self.max_hp)
        self.now = 0.0
        self.respawn_at = None
        self.sc_level = PS.Schema.load(SKILL_LEVEL)

    def start_place(self):
        """where the start state (the replay's first keyframe) puts the champion"""
        import x_buf
        tm, head, buf = x_buf.buffers(MOVE, 0x18, 1)[0]
        for e in waypoints.parse(buf):
            if e['net'] == self.net:
                return waypoints.to_world(e['points'][-1])
        raise KeyError(f'net id {self.net:#x} is not in the start state')

    @property
    def xy(self):
        return self.place()

    poly = None                  # a walk through several points: (world16.Path, start time)

    def place(self, t=None):
        t = self.now if t is None else t
        if self.poly is not None:
            path, t0 = self.poly
            return path.at((t - t0) * self.speed)
        d = math.dist(self.a, self.b)
        if d < 1e-6:
            return self.b
        k = min(1.0, max(0.0, (t - self.t0) * self.speed / d))
        return (self.a[0] + (self.b[0] - self.a[0]) * k, self.a[1] + (self.b[1] - self.a[1]) * k)

    def walk(self, t, goal):
        """a walk to goal around walls and buildings: the map's navigation grid (navgrid.py, 16.20's own grid), as
        the real server paths its units [the user: our champion walked through the nexus] -> the movement packet"""
        import navgrid
        import world16
        here = self.place(t)
        pts = navgrid.grid().path(here, goal) or [here, goal]
        pts = [here] + [p for p in pts[1:] if math.dist(p, here) > 1.0] or [here]
        self.poly = (world16.Path(pts), t) if len(pts) > 1 else None
        self.a, self.b, self.t0 = here, pts[-1], t
        return self.move_packet(t, pts)

    def stand(self, t):
        here = self.place(t)
        self.poly = None
        self.a = self.b = here
        self.t0 = t
        return self.move_packet(t, [here])

    def read_order(self, data):
        """a client packet 1032 after its id -> dict(sender, place (x, z), target net id, kind byte as the client
        holds it in memory) or None"""
        sender, n = netid16.decode(data)
        v = self.c2s.decode(self.order_spec, data[n:])
        if v is None:
            return None
        return {'sender': sender, 'place': struct.unpack('<ff', v[0x18]), 'target': struct.unpack('<I', v[0x20])[0],
                'kind': v[0x24][0], 'rest': v['rest']}

    def move_packet(self, t, points):
        """(channel, packet id, net id, body): our movement packet for the champion along world points"""
        self.counter = max(self.counter + 1, 2000 + int(t * COUNTER_RATE))
        entry = lol_packets.waypoint_entry(self.net, [to_cell(p) for p in points], self.speed, flags=0)
        body = self.sc.encode({'+0x10': struct.pack('<H', 1).hex(), '+0x18': {'text': entry.hex()},
                               '+0x28': struct.pack('<I', self.counter).hex()})
        return MOVE_CHANNEL, MOVE, 0, body

    def replication(self, t, values):
        import repl16
        self.repl_counter += 1
        self.values.update(values)
        return (2, repl16.REPL, 0, repl16.packet([(self.net, values, repl16.HERO)], game_time=t, counter=self.repl_counter))

    def start(self, t):
        """the champion's state right after the start state (the start state itself carries no replication)"""
        return [self.replication(t, dict(self.values))]

    def on_skill_up(self, data, t):
        """client packet 544 after its id: one header byte whose low 3 bits say the slot (0 Q, 1 W, 2 E by constant
        modes; else a byte follows). Answer as the replay does at Kennen's first level-up: 810 (+0x10 1, +0x11 the new
        level, +0x12 the slot, +0x13 points left), then the slot's bit in mReplicatedSpellCanCastBitsLower1."""
        sender, n = netid16.decode(data)
        body = data[n:]
        mode = body[0] & 7
        slot = self.skill['const_modes'].get(str(mode))
        if slot is None and mode == self.skill['fixed_mode'] and len(body) > 1:
            slot = self.skill['fixed'].get(str(body[1]))
        if slot is None or not 0 <= slot <= 3 or self.points <= 0:
            return [], slot
        self.levels[slot] += 1
        self.points -= 1
        level = self.sc_level.encode({'+0x10': '01', '+0x11': f'{self.levels[slot]:02x}', '+0x12': f'{slot:02x}',
                                      '+0x13': f'{self.points:02x}'})
        bits = int(self.values.get('mReplicatedSpellCanCastBitsLower1', 0)) | (1 << slot)
        return [(1, SKILL_LEVEL, self.net, level), self.replication(t, {'mReplicatedSpellCanCastBitsLower1': bits})], slot

    def on_order(self, data, t, world=None):
        """-> packets to send for a client order: with a target net id of a unit of our world it is an attack order
        (tick() walks into range and attacks); else a move to the clicked place, in a straight line"""
        o = self.read_order(data)
        if o is None or not self.alive:
            return [], o
        u = world.unit(o['target']) if world is not None and o['target'] else None
        if u is not None and u.alive and u.team != self.team:
            self.target = o['target']
            return [], o
        self.target = None
        if not (0 < o['place'][0] < 16000 and 0 < o['place'][1] < 16000):
            return [], o
        here = self.place(t)
        if math.dist(here, o['place']) < 1.0 or math.dist(self.b, o['place']) < 1.0 and t - self.t0 < 0.05:
            return [], o          # the client sends each order twice: the second copy changes nothing
        return [self.walk(t, o['place'])], o

    ATTACK_PERIOD = 1.6      # Kennen's 0.625 attacks a second [the usual value]
    WINDUP = 0.2             # [approximation]
    MISSILE = 1600.0         # [approximation]

    def tick(self, t, world):
        """the attack order: walk until the target is in range, then attack it (the replay's champion attack packets
        906 + 972 with our ids; the damage lands through the world) -> packets"""
        out = []
        self.now = t
        if not self.alive:
            if self.respawn_at is not None and t >= self.respawn_at:
                out += self.returns(t, world)
            return out
        tgt = world.unit(self.target) if self.target else None
        if tgt is None or not tgt.alive:
            self.target = None
            return out
        here, there = self.place(t), tgt.place()
        d = math.dist(here, there) - (88.0 if getattr(tgt, 'is_structure', False) else 0.0)
        if d > self.range + 2 * 48.0:
            if t - self.last_path > 0.25:          # (re)path towards it, at most four times a second
                self.last_path = t
                out.append(self.walk(t, there))
            return out
        if math.dist(self.b, here) > 1.0 or self.poly is not None:     # in range and still walking: stand
            out.append(self.stand(t))
        if t >= self.next_attack and world.can_fight():
            import copy
            import roles16 as R
            self.next_attack = t + self.ATTACK_PERIOD
            self.attacks += 1
            if self.attack_net is None:
                self.attack_net = world.new_net()
            v = copy.deepcopy(world.templates[str(R.HERO_ATTACK)])
            v['+0x10'].update({'+0x8': struct.pack('<I', self.attacks).hex(), '+0xd': '40' if self.attacks % 2 else '41',
                               '+0x10': struct.pack('<fff', there[0], 50.0, there[1]).hex(),
                               '+0x1c': struct.pack('<I', self.attack_net).hex(), '+0x20': struct.pack('<I', tgt.net).hex()})
            v['+0x48'] = struct.pack('<ff', here[0], here[1]).hex()
            out.append((1, R.HERO_ATTACK, self.net, world.sc[R.HERO_ATTACK].encode(v)))
            out.append((1, R.ATTACK_972, self.net, world.sc[R.ATTACK_972].encode(
                world.field(R.ATTACK_972, {'+0x10': struct.pack('<I', tgt.net).hex(),
                                           '+0x14': struct.pack('<fff', there[0], 50.0, there[1]).hex(), '+0x20': '02'}))))
            world.push(t + self.WINDUP + d / self.MISSILE, lambda t2, tgt=tgt: world.hit(t2, self, tgt, share=1.0))
        return out

    RESPAWN = 12.0           # seconds dead at level 1 [the usual value; the live match: 38.5 s at minute 18]

    def take(self, t, src, damage, world):
        """an attack lands on the champion: the damage packets as for a minion, the new health, death at zero"""
        import roles16 as R
        if not self.alive:
            return
        base = {'+0x14': struct.pack('<I', self.net).hex(), '+0x1c': struct.pack('<I', src.net).hex()}
        world.send(R.DAMAGE, self.net, world.field(R.DAMAGE, dict(base, **{'+0x10': struct.pack('<f', damage).hex(), '+0x19': '01'})))
        self.hp = max(0.0, self.hp - damage)
        world.out.append(self.replication(t, {'mHP': self.hp}))
        if self.hp <= 0:
            self.dies(t, src, world)

    def dies(self, t, src, world):
        """the live server's death of a champion (events16 'hero_dies': 437 score, 166 + 421 with the time to come
        back, 131, 1050 ...), the champion stands where it fell"""
        self.alive = False
        self.target = None
        here = self.place(t)
        self.poly = None
        self.a = self.b = here
        self.t0 = t
        self.respawn_at = t + self.RESPAWN
        self.deaths = getattr(self, 'deaths', 0) + 1
        score = {'+0x10': struct.pack('<I', getattr(self, 'kills', 0)).hex(), '+0x14': struct.pack('<I', self.deaths).hex(),
                 '+0x18': struct.pack('<I', getattr(self, 'assists', 0)).hex()}
        timer = struct.pack('<f', self.RESPAWN).hex()
        tm = struct.pack('<f', t).hex()

        def death(v):
            v['+0x10']['+0x20'] = struct.pack('<fff', here[0], 50.0, here[1]).hex()
            v['+0x50'] = struct.pack('<I', src.net).hex()
            v['+0x54'] = timer
            return v
        if world.structs is not None:
            for dt, ch, pid, net, body in world.structs.ev.make('hero_dies', {'H': self.net, 'K': src.net},
                                                                  {166: {'+0x10': timer}, 421: death, 437: score,
                                                                   1050: {'+0x14': tm, '+0x18': tm}}, skip=(515, 447)):
                if pid == 437 and net != self.net:
                    continue                      # the killer's own score: not kept for units of ours yet
                world.out.append((ch, pid, net, body))
        world.out.append(self.move_packet(t, [here]))
        world.events.append(('hero_died', self.net, src.net))

    def returns(self, t, world):
        """back at the fountain with full health ('hero_returns': 1050 ...)"""
        self.alive = True
        self.respawn_at = None
        self.hp = self.max_hp
        self.poly = None
        self.a = self.b = self.home
        self.t0 = t
        tm = struct.pack('<f', t).hex()
        out = []
        if world.structs is not None:
            out += [(ch, pid, net, body) for dt, ch, pid, net, body in
                    world.structs.ev.make('hero_returns', {'H': self.net},
                                          {1050: {'+0x14': tm, '+0x18': tm},
                                           158: {'+0x14': struct.pack('<ff', self.home[0], self.home[1]).hex()}})]
        out.append(self.move_packet(t, [self.home]))
        out.append(self.replication(t, {'mHP': self.hp}))
        return out

    # ------------------------------------------------------------------ economy
    # experience needed for each level, cumulative [the usual table; measured live: level 2 at 341 >= 280, 3 at 682,
    # 4 at 1160, 5 at 1731]
    LEVELS = [0, 280, 660, 1140, 1720, 2400, 3180, 4060, 5040, 6120, 7300, 8580, 9960, 11440, 13020, 14700, 16480, 18360]
    PASSIVE_FROM, PASSIVE_STEP, PASSIVE_GOLD = 65.0, 0.5, 1.02   # [measured live: +1.02 every 0.5 s from 65 s]

    def set_champion(self, champion):
        """the champion's base stats and their growth per level, from its CharacterRecord (game16's bins)"""
        import bin_tree as BT
        rec = BT.character_record(champion) or {}

        def val(name, default):
            v = rec.get(name + 'Modifiable', rec.get(name))
            if isinstance(v, dict):
                v = v.get('baseValue', default)
            return float(v) if isinstance(v, (int, float)) else default
        self.champion = champion
        self.base = {'hp': val('baseHP', 600.0), 'hp_lvl': val('hpPerLevel', 90.0), 'ad': val('baseDamage', 60.0),
                     'ad_lvl': val('damagePerLevel', 3.0), 'armor': val('baseArmor', 30.0), 'armor_lvl': val('armorPerLevel', 4.0),
                     'range': val('attackRange', 175.0), 'speed': val('baseMoveSpeed', 340.0)}
        self.level = 1
        self.xp = 0.0
        self.range = self.base['range']
        self.damage = self.base['ad']
        self.next_passive = self.PASSIVE_FROM

    def stats_at(self, level):
        b = self.base
        g = (level - 1) * (0.7025 + 0.0175 * (level - 1))      # the usual growth curve of per-level stats
        return {'mMaxHP': b['hp'] + b['hp_lvl'] * g, 'mBaseAttackDamage': b['ad'] + b['ad_lvl'] * g,
                'mArmor': b['armor'] + b['armor_lvl'] * g}

    def gain_gold(self, t, amount, world=None):
        self.gold += amount
        self.gold_total = getattr(self, 'gold_total', float(self.values.get('mGoldTotal', self.gold))) + amount
        pk = self.replication(t, {'mGold': self.gold, 'mGoldTotal': self.gold_total})
        if world is not None:
            world.out.append(pk)
        return pk

    def gain_xp(self, t, amount, world):
        """experience: the floating number (1024 {champion, amount}), mExp, and every level reached: 969 {1, level},
        a skill point, the new stats [measured live: 1024 / 969 at a level-up]"""
        if not hasattr(self, 'level'):
            return
        self.xp += amount
        sc = world.structs.ev.schema if world.structs is not None else None
        if sc is not None:
            world.out.append((1, 1024, 0, sc(1024).encode({'+0x10': struct.pack('<I', self.net).hex(),
                                                           '+0x14': struct.pack('<f', amount).hex()})))
        vals = {'mExp': self.xp}
        while self.level < 18 and self.xp >= self.LEVELS[self.level]:
            self.level += 1
            self.points += 1
            st = self.stats_at(self.level)
            grow = st['mMaxHP'] - self.max_hp
            self.max_hp = st['mMaxHP']
            self.hp = min(self.max_hp, self.hp + grow)
            self.damage = st['mBaseAttackDamage']
            vals.update(st, mHP=self.hp, mLevelRef=self.level)
            if sc is not None:
                world.out.append((1, 969, self.net, sc(969).encode({'+0x10': '01', '+0x11': f'{self.level:02x}'})))
        world.out.append(self.replication(t, vals))

    def economy(self, t, world):
        """passive gold"""
        out = []
        if hasattr(self, 'next_passive') and t >= self.next_passive:
            steps = int((t - self.next_passive) / self.PASSIVE_STEP) + 1
            self.next_passive += steps * self.PASSIVE_STEP
            out.append(self.gain_gold(t, steps * self.PASSIVE_GOLD))
        return out

    def take_events(self, t, world):
        """what the world did for this champion since the last call (gold for a kill) -> packets"""
        out = []
        for ev in [e for e in world.events if e[1] == self.net]:
            world.events.remove(ev)
            if ev[0] == 'gold':
                out.append(self.gain_gold(t, ev[2]))
        return out


if __name__ == '__main__':
    import pkt_schema as PS
    import pkt_tree as PT
    h = Hero(0x400000ae)
    print('start place', tuple(round(x, 1) for x in h.a))
    # a real order captured from the client (data/exe1620/match_click1), after its id
    data = bytes.fromhex('64fa151df4b1d131f48a619d9cffd0cbab647e121a9f12478ff6957184e08e4843438543a1')
    pk, o = h.on_order(data, 26.0)
    print('order:', {k: (hex(v) if k in ('sender', 'target') else v) for k, v in o.items() if k != 'rest'})
    ch, pid, net, body = pk[0]
    T = PT.Tree(MOVE)
    v = PS.decode(T, h.sc, PT.P.wire(pid, net, body))
    ents = waypoints.parse(bytes.fromhex(v['+0x18']['text']))
    print(f'our packet {pid} ({len(body)} B) read by the client\'s reader: count {int.from_bytes(bytes.fromhex(v["+0x10"]), "little")}, '
          f'counter {int.from_bytes(bytes.fromhex(v["+0x28"]), "little")}, entry net {ents[0]["net"]:#x} speed {ents[0]["speed"]} '
          f'points {[tuple(round(c, 1) for c in waypoints.to_world(p)) for p in ents[0]["points"]]}')
    print('place 1 s later', tuple(round(x, 1) for x in h.place(27.0)))
