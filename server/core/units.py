"""The unit model of the simulation: what every attackable thing on the map is made of.

A unit has a record (the game's CharacterRecord numbers, gamedata.py), a level, modifiers from items and buffs, the
totals computed from those, health, a place, a path it walks, a basic attack (target -> windup -> missile -> hit),
and the replicated values the client holds about it: set() notes a changed value, the game sends the changes at the
end of the frame (packet 287), as the real server does.

Ranges are LoL's: a unit reaches a target when the distance between their centres is at most its attack range plus
both gameplay radii.
"""
import math
import os

from . import gamedata as G
from . import packets as P

ORDER, CHAOS, NEUTRAL = 100, 200, 300
STATS = ('hp', 'par', 'ad', 'ap', 'armor', 'mr', 'as', 'ms', 'ms_pct', 'hp_regen', 'par_regen', 'crit', 'haste', 'lifesteal',
         'lethality', 'armor_pen', 'magic_pen', 'magic_pen_pct', 'range', 'hp_regen_pct', 'par_regen_pct', 'tenacity', 'omnivamp')


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


FRAME = 0.26729 / 8.0          # [m] the real server's frame: 33.41 ms (8 a script update; game.DT)
CHASE_REPEAT = 2.0 * FRAME     # [m] the 515 repeated every two frames while a unit follows its target


class Unit:
    kind = 'unit'
    repl_cls = None
    is_structure = False
    is_hero = False
    can_move = True

    def __init__(self, game, net, team, name, pos, base):
        self.game, self.net, self.team, self.name = game, net, team, name
        self.pos = (float(pos[0]), float(pos[1]))
        self.base = base
        self.level = 1
        self.mods = {}                  # source -> {stat: amount}
        self.bonus = dict.fromkeys(STATS, 0.0)
        self.alive = True
        self.targetable = True
        self.radius = float(base.get('radius', 48.0) or 48.0)
        self.sight = float(base.get('sight', 1200.0) or 1200.0)
        self.sent, self.dirty = {}, {}
        self.reveal_until = 0.0          # shown in brush until then (it attacked or cast)
        # movement
        self.path = None                # the points still to walk to, in order
        self.facing = (1.0, 0.0)
        # the basic attack
        self.target = None              # net id
        self.attack_ready = 0.0         # when the next attack may begin
        self.windup_end = None
        self.windup_target = None
        self.attack_id = None           # the net id its attacks carry (its missile's)
        self.attacks = 0
        self.missile_speed = float(base.get('missile_speed', 0.0) or 0.0)
        self.attack_slots = 1
        self.attack_name = None         # the variant of the attack under way (its damage carries the name)
        self.attack_crit = False
        self.last_hit_by = {}           # net id of a champion -> time of its last damage (assists)
        self.cc_until = 0.0             # cannot act (stun)
        self.root_until = 0.0           # cannot move
        self.speed_mult = 1.0
        self.recompute(first=True)
        self.hp, self.par = self.max_hp, self.max_par

    # ------------------------------------------------------------------ stats
    def add_mods(self, source, mods):
        self.mods[source] = mods
        self.recompute()

    def remove_mods(self, source):
        if self.mods.pop(source, None) is not None:
            self.recompute()

    def recompute(self, first=False):
        b, L = self.base, self.level
        bonus = dict.fromkeys(STATS, 0.0)
        for m in self.mods.values():
            for k, v in m.items():
                bonus[k] = bonus.get(k, 0.0) + v
        self.bonus = bonus
        old_max = getattr(self, 'max_hp', None)
        self.max_hp = G.level_stat(b['hp'], b.get('hp_lvl', 0.0), L) + bonus['hp']
        self.max_par = G.level_stat(b.get('par', 0.0), b.get('par_lvl', 0.0), L) + bonus['par']
        self.base_ad = G.level_stat(b['ad'], b.get('ad_lvl', 0.0), L)
        self.ad = self.base_ad + bonus['ad']
        self.ap = bonus['ap']
        self.base_armor = G.level_stat(b.get('armor', 0.0), b.get('armor_lvl', 0.0), L)
        self.base_mr = G.level_stat(b.get('mr', 0.0), b.get('mr_lvl', 0.0), L)
        self.armor, self.mr = self.base_armor + bonus['armor'], self.base_mr + bonus['mr']
        as_bonus = G.level_stat(0.0, b.get('as_lvl', 0.0), L) / 100.0 + bonus['as']
        self.as_bonus = as_bonus
        self.attack_speed = min(3.0, b.get('as', 0.625) + b.get('as_ratio', b.get('as', 0.625)) * as_bonus)
        self.range = b.get('range', 125.0) + bonus['range']
        ms = (b.get('speed', 325.0) + bonus['ms']) * (1.0 + bonus['ms_pct'])
        if ms > 490:                                    # LoL's soft caps of move speed [m: minions at 425 show 423]
            ms = ms * 0.5 + 230
        elif ms > 415:
            ms = ms * 0.8 + 83
        elif ms < 220:
            ms = ms * 0.5 + 110
        self.move_speed = ms
        self.hp_regen = (b.get('hp_regen', 0.0) + b.get('hp_regen_lvl', 0.0) * (L - 1)) * (1.0 + bonus['hp_regen_pct']) + bonus['hp_regen']
        self.par_regen = (b.get('par_regen', 0.0) + b.get('par_regen_lvl', 0.0) * (L - 1)) * (1.0 + bonus['par_regen_pct']) + bonus['par_regen']
        self.crit = min(1.0, bonus['crit'])
        if old_max is not None and not first and self.max_hp != old_max and self.alive:
            self.hp = max(1.0, self.hp + (self.max_hp - old_max)) if self.max_hp > old_max else min(self.hp, self.max_hp)
        if not first:
            self.replicate_stats()

    def replicate_stats(self):
        """overridden per kind: the replicated names of the totals"""

    @property
    def speed(self):
        return self.move_speed * self.speed_mult

    def attack_time(self):
        return 1.0 / max(0.1, self.attack_speed)

    def windup_time(self):
        b = self.base
        if b.get('attack_total') and b.get('attack_cast'):       # data gives both times (minions, monsters)
            return b['attack_cast'] * (b['attack_total'] and (self.attack_time() / b['attack_total']) or 1.0)
        return self.attack_time() * b.get('windup', 0.3)

    # ------------------------------------------------------------------ replication
    def set(self, name, value):
        if self.sent.get(name) != value:
            self.dirty[name] = value
        else:
            self.dirty.pop(name, None)

    def set_many(self, values):
        for k, v in values.items():
            self.set(k, v)

    def take_dirty(self):
        d, self.dirty = self.dirty, {}
        self.sent.update(d)
        return d

    def set_hp(self, hp):
        self.hp = max(0.0, min(self.max_hp, hp))
        self.set('mHP', self.hp)

    def heal(self, amount):
        """healing with the unit's healing amplification (heal_amp: + share, Aatrox's World Ender) -> health gained"""
        if amount <= 0 or not self.alive:
            return 0.0
        before = self.hp
        self.set_hp(self.hp + amount * (1.0 + getattr(self, 'heal_amp', 0.0)))
        return self.hp - before

    # ------------------------------------------------------------------ movement
    @property
    def moving(self):
        return bool(self.path)

    def go(self, points, send=True):
        """walk through these points from where it stands"""
        pts = [(float(p[0]), float(p[1])) for p in points if dist(p, self.pos) > 1.0] if points else []
        if not pts or not self.can_move:
            return self.stop() if self.path else None
        self.path = pts
        if send:
            self.game.q_moves.append(self.game.pk.move_entry(self.net, [self.pos] + pts, self.speed))

    def path_to(self, goal):
        """walk to a place around walls (the navigation grid)"""
        pts = self.game.nav.path(self.pos, goal)
        if not pts:
            pts = [self.pos, goal]
        self.go(pts[1:])

    def stop(self, send=True):
        self.path = None
        if send:
            self.game.q_moves.append(self.game.pk.move_entry(self.net, [self.pos], self.speed))

    def teleport(self, p):
        """at once to another place [m: a movement entry of one point with the unit's own teleport counter]"""
        import lol_packets
        self.pos = (float(p[0]), float(p[1]))
        self.path = None
        self.teleports = getattr(self, 'teleports', 1) + 1
        self.game.q_moves.append(lol_packets.waypoint_teleport(self.net, P.cell(self.pos), self.speed, self.teleports & 0xff, flags=0))

    def advance(self, dt):
        """a frame of walking -> True when the last point is reached in this frame"""
        if not self.path:
            return False
        t = self.game.t
        if t < self.root_until or (t < self.cc_until and t >= getattr(self, 'forced_until', 0.0)):
            return False                                 # held; a charmed / feared unit is walked by the spell
        step = self.speed * dt
        while self.path and step > 0:
            nxt = self.path[0]
            d = dist(self.pos, nxt)
            if d <= step:
                if d > 0.01:
                    self.facing = ((nxt[0] - self.pos[0]) / d, (nxt[1] - self.pos[1]) / d)
                self.pos = nxt
                step -= d
                self.path.pop(0)
            else:
                self.facing = ((nxt[0] - self.pos[0]) / d, (nxt[1] - self.pos[1]) / d)
                self.pos = (self.pos[0] + self.facing[0] * step, self.pos[1] + self.facing[1] * step)
                step = 0
        if not self.path:
            self.path = None
            return True
        return False

    # ------------------------------------------------------------------ the basic attack
    def reach(self, tgt):
        return self.range + self.radius + tgt.radius

    def in_reach(self, tgt, slack=0.0):
        return dist(self.pos, tgt.pos) <= self.reach(tgt) + slack

    def can_target(self, tgt):
        return (tgt is not None and tgt.alive and tgt.targetable and tgt.team != self.team and
                self.game.seen_by(self.team, tgt))

    def attack_tick(self, t):
        """one frame of the basic attack against self.target -> 'idle' (no target), 'far' (out of reach: the caller
        decides whether to chase), 'windup', 'wait' (in reach, between attacks)"""
        g = self.game
        self.tell_hero_target()
        if self.windup_end is not None:
            if t >= self.windup_end:
                self.fire(t)
            return 'windup'
        tgt = g.units.get(self.target) if self.target else None
        if not self.can_target(tgt):
            self.target = None
            self.end_engagement()
            return 'idle'
        if t < self.cc_until:
            return 'wait'
        if not self.in_reach(tgt):
            if getattr(self, 'told_target', None) is not None:
                # the chain below only follows the champion the unit WAS attacking [m: the replays' chains]
                self.chase_stop = (tgt.net, t) if self.told_target == tgt.net else None
                self.end_engagement()
            elif self.kind == 'monster' and tgt.is_hero and getattr(self, 'chase_stop', None) and self.chase_stop[0] == tgt.net \
                    and t - self.chase_stop[1] >= CHASE_REPEAT - 1e-6:
                # [m: the replays - 156 chains (910 packets) behind a champion, 27 behind anything else; 10-13: all of
                # them monsters - 0 chains among 17k lane minion 515s] a monster that follows the champion it was
                # attacking says again every two frames that it does not attack, until it attacks again
                self.chase_stop = (tgt.net, t)
                g.q += g.pk.attack_stop(self)
            return 'far'
        if self.path:
            self.stop()
        if t >= self.attack_ready:
            self.start_attack(t, tgt)
            return 'windup'
        return 'wait'

    def start_attack(self, t, tgt):
        g = self.game
        if getattr(self, 'stealth_until', 0.0) > t:
            reveal(self)
        self.attacks += 1
        if self.attack_id is None:
            self.attack_id = g.new_net()
        d = dist(self.pos, tgt.pos) or 1.0
        self.facing = ((tgt.pos[0] - self.pos[0]) / d, (tgt.pos[1] - self.pos[1]) / d)
        names, weights = self.attack_variants()
        if self.is_hero and getattr(g, 'kits', None) is not None:
            # a kit's form whose attacks are other variants of the champion's list (Aatrox's World Ender: 4th / 5th)
            ch = g.kits.call(self, 'attack_choices', self)
            if ch:
                weights = [ch.get(i, 0.0) for i in range(len(names))]
        k = g.rng.choices(range(len(names)), weights)[0] if len(names) > 1 else 0
        slot = 0x40 + k
        self.attack_name = names[k]
        # [m: the replays' 906] a critical strike is told when the attack begins: slot 0x49, the crit attack's name
        self.attack_crit = bool(self.is_hero and self.crit > 0 and g.rng.random() < self.crit)
        if self.attack_crit:
            slot = 0x49
            self.attack_name = getattr(self.champ, 'crit_attack', None) or self.attack_name
        if getattr(self, 'own_attack_slot', None) is not None:
            slot = self.own_attack_slot
        spell = None
        if self.is_hero and getattr(g, 'kits', None) is not None:
            # a kit's empowered attack: its own slot, name and cast struct (Aatrox's Deathbringer Stance)
            ov = g.kits.call(self, 'attack_override', self, tgt)
            if ov:
                slot, self.attack_name, self.attack_crit = ov['slot'], ov['name'], False
                spell = dict(ov, t=t, cast_time=self.windup_time(), total_time=self.attack_time())
        # [the replays: 261 minions / monsters / turrets, 13 shots each but 4 attack packets each] a unit that is no
        # champion is told to attack ONCE per target (390); the client repeats the swings itself (a ranged one's
        # missiles still come one by one, 938) until the unit is told to stop (515) or given another target
        self.chase_stop = None
        if self.is_hero or getattr(self, 'told_target', None) != tgt.net:
            if not self.is_hero and getattr(self, 'told_target', None) is not None:
                g.q += g.pk.attack_stop(self)            # [m] the engagement before ends with its 515
            g.q += g.pk.attack(self, tgt, self.attack_id, self.attacks, slot, spell)
            self.told_target = tgt.net
        elif self.kind == 'monster':
            # [m: the replays' camps - Gromp, Red, Krugs: a 972 at every attack, the 390 only for a new target]
            g.q += g.pk.attack_aim(self, tgt)
        self.windup_end = t + self.windup_time()
        self.attack_began = t
        self.reveal_until = t + 1.0
        self.windup_target = tgt.net
        self.attack_ready = t + self.attack_time()
        if self.is_hero and getattr(g, 'statbuffs', None) is not None:
            g.statbuffs.on_attack(self)
        if getattr(g, 'renewals', None) is not None:
            g.renewals.on_attack(self, tgt)
        if self.is_hero and getattr(g, 'itembuffs', None) is not None:
            g.itembuffs.on_attack(self, tgt)
        if self.is_hero and getattr(g, 'kits', None) is not None:
            g.kits.call(self, 'attack_start', self, tgt)
        if self.is_hero and getattr(g, 'fx', None) is not None:
            g.fx.on_attack_start(self, tgt)
        self.on_attack(t, tgt)

    def tell_hero_target(self):
        """447 [m: the replays - 383 from minions, 170 from champions in 150 s; half name a champion, half 0]: a unit
        tells the champion it has taken as its target, and 0 when its target is no longer a champion"""
        tgt = self.game.units.get(self.target) if self.target else None
        now = tgt.net if tgt is not None and tgt.is_hero and tgt.alive else 0
        if now != getattr(self, 'hero_target_told', 0):
            self.hero_target_told = now
            self.game.q += self.game.pk.target(self, now)

    def end_engagement(self):
        """the unit stops attacking the target it was attacking: 515 [the replays: 3056 of them in 150 s], and a unit
        that is no champion has its next attack told again. A champion too, when it had attacked that target [m: 69
        of the replay's 515 follow the death of a champion's target]"""
        if getattr(self, 'told_target', None) is not None:
            self.told_target = None
            lost, self.target_lost = getattr(self, 'target_lost', False), False
            # [m: 2 replays, 1,600 moves 0.2 - 0.5 s after a champion's attack began with no 515; its 515s come in the
            # windup (cancel_attack) or when its target dies] a champion that walks off after its shot says nothing
            if self.alive and (not self.is_hero or lost):
                self.game.q += self.game.pk.attack_stop(self)

    def attack_variants(self):
        """the unit's attack variants' names and chances [data: basicAttack + extraAttacks]"""
        names = self.base.get('attack_names') or [self.base.get('attack_name') or f'{self.name}BasicAttack']
        return names, self.base.get('attack_weights') or [1.0] * len(names)

    def on_attack(self, t, tgt):
        """hook: an attack has begun (minions call for help, turrets warn)"""

    def cancel_attack(self):
        """the windup is thrown away (an order to move): the attack may begin again at once"""
        if self.windup_end is not None:
            self.windup_end = None
            self.attack_ready = self.game.t
            self.game.q += self.game.pk.attack_stop(self)

    def fire(self, t):
        g = self.game
        self.windup_end = None
        tgt = g.units.get(self.windup_target)
        if tgt is None or not tgt.alive:
            return
        if self.is_hero and getattr(g, 'statbuffs', None) is not None:
            g.statbuffs.on_fire(self, tgt)
        if self.is_hero and getattr(g, 'kits', None) is not None:
            g.kits.call(self, 'fire', self, tgt)            # the windup is over (Graves' shells)
        if self.missile_speed > 0:
            g.q += g.pk.missile_launch(self, self.attack_id)
            flight = max(0.0, dist(self.pos, tgt.pos) - tgt.radius) / self.missile_speed
            g.at(t + flight, lambda t2, tgt=tgt: self.land(t2, tgt, True))
        else:
            self.land(t, tgt, False)

    def land(self, t, tgt, missile):
        g = self.game
        if missile:
            g.q += g.pk.missile_end(self.attack_id)
        if tgt.alive:
            g.basic_hit(self, tgt)

    # ------------------------------------------------------------------ misc
    def start_values(self):
        """the replicated values the client must be given when the unit appears"""
        return {}

    def __repr__(self):
        return f'<{self.kind} {self.name} {self.net:#x} team {self.team} hp {self.hp:.0f}/{self.max_hp:.0f} at ({self.pos[0]:.0f}, {self.pos[1]:.0f})>'


def reveal(u):
    """the unit's invisibility ends (it attacked, or cast a spell that breaks it): its invisibility buffs end, its
    fade is undone [m: the wards' 29 pops the 596 fade]"""
    g = u.game
    u.stealth_until = 0.0
    for key, b in list(getattr(u, 'buff_list', {}).items()):
        if b.get('args', (0, 0, 0))[2] == 6:
            u.buff_list.pop(key, None)
            g.q += g.pk.buff_remove(u.net, b['slot'], b['hash'])
    for fid in getattr(u, 'fades', [])[::-1]:
        g.q.append((1, 29, u.net, g.pk.enc(29, {'+0x10': fid.to_bytes(2, 'little').hex()})))
    u.fades = []


class Minion(Unit):
    kind = 'minion'
    repl_cls = 'lane_minion'

    def __init__(self, game, net, team, name, pos, base, mtype, wave, lane, barracks_net):
        super().__init__(game, net, team, name, pos, base)
        self.mtype, self.wave, self.lane, self.barracks_net = mtype, wave, lane, barracks_net
        self.lane_points = None         # the lane's waypoints in walking order
        self.lane_i = 0                 # the next waypoint it walks to
        self.spot = None
        self.next_think = 0.0
        self.spawn_t = game.t
        self.leash = None

    def replicate_stats(self):
        self.set_many({'mMaxHP': self.max_hp, 'mBaseAttackDamage': self.base_ad, 'mArmor': self.armor,
                       'mAttackRange': self.range, 'mMoveSpeed': self.speed})

    def on_attack(self, t, tgt):
        if tgt.is_hero:
            pass


class Monster(Unit):
    kind = 'monster'
    repl_cls = 'lane_minion'        # [m] a jungle monster's values travel in the lane minion's tables

    def __init__(self, game, net, name, pos, base, camp):
        super().__init__(game, net, NEUTRAL, name, pos, base)
        self.camp = camp
        self.home = self.pos
        self.next_think = 0.0

    def replicate_stats(self):
        self.set_many({'mMaxHP': self.max_hp, 'mBaseAttackDamage': self.base_ad, 'mArmor': self.armor, 'mMoveSpeed': self.speed})


class Structure(Unit):
    is_structure = True
    can_move = False

    def __init__(self, game, net, team, name, pos, base, lane, tier):
        super().__init__(game, net, team, name, pos, base)
        self.lane, self.tier = lane, tier        # tier: outer inner inhibitor nexus fountain | dampener | hq
        self.targetable = False


class Turret(Structure):
    kind = 'turret'
    repl_cls = 'AITurretCommon'

    def __init__(self, game, net, team, name, pos, base, lane, tier):
        super().__init__(game, net, team, name, pos, base, lane, tier)
        self.next_think = 0.0
        self.heat = 0                   # consecutive shots at a champion (the damage grows)
        self.first_shot = True

    def replicate_stats(self):
        self.set_many({'mMaxHP': self.max_hp, 'mBaseAttackDamage': self.base_ad, 'mArmor': self.armor})

    def windup_time(self):
        return 0.266                    # [m] the missile leaves 0.266 s after the attack packet


class Inhibitor(Structure):
    kind = 'inhibitor'
    repl_cls = 'BarracksDampenerCommon'
    respawn_at = None
    falls = 0                            # how many times it has been destroyed


class Nexus(Structure):
    kind = 'nexus'
    repl_cls = 'HQCommon'
