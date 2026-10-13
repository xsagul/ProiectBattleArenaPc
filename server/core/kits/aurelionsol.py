"""Aurelion Sol, the Star Forger - the live wiki checked against the 16.20 data and the replays.

Cosmic Creator (P) [wiki; m: replays]: Stardust, a counter (430) on AurelionSolPassive (d5ca630c, type 1 [a: its add is
  before the replays start]) - one 430 per gain (+1 / +2 / +5). Breath of Light's bursts + (0.031 x Stardust) % max
  health; Astral Flight + 7.5 range each; Singularity's radius sqrt(275^2 + 900 / pi x S) (data OuterRadiusAreaPerStack),
  its centre half of it [wiki: 137.5 / 8.46], its execute + 0.026 % each; Falling Star's radius as Singularity's.
Breath of Light (Q) [wiki, data; m]: a channel (AurelionSolQ, type 2, 100 s, at +0.033), its beam 140 wide and 750 - 920
  long (by level) turning 180 / s (towards the cast's target [a: no cursor here]); every 0.1 s [m: 3 frames apart, data
  mChargeUpdateInterval] the first enemy on it takes (45 - 105 + 55 % AP) x 0.1 and the enemies within 250 of it [m: 90 %
  of 4194 secondary hits] half; each target's first hit gives AurelionSolQDebuff (d6b1420d, 10 s). A full second on the
  same primary [m: the 11th tick] bursts 60 - 100 + 30 % AP and the Stardust part (both named AurelionSolQ; monsters at
  most 300 from health) and gives 2 Stardust from champions; the timer resets after 1 s off it. Mana 7.5 - 12.5 every
  0.25 s; it ends by a recast, moving, attacking, another cast, crowd control, no mana or 3.25 s (none at rank 5 [data
  9999]); then its 3 s cooldown (635) - within 0.25 s a 1 s lockout instead.
Astral Flight (W) [wiki, data; m]: 0.434 s after the cast [m: 1140] a flight of 1500 + 7.5 x Stardust at 340 + his move
  speed, half while Breath of Light channels; it resets Q, during it Q has no cooldown and no maximum and its ticks deal
  108 - 112 % (TrueDamageBonus), with 3e912a06 beside AurelionSolQ [m]; AurelionSolW (type 2, 4 s at +0.401, then 25000
  [m: 282]); a recast after 0.5 s or the arrival ends it (78 back to AurelionSolW), and the channel with it. A champion
  takedown within 3 s of damaging them cuts 90 % of its total cooldown (after the flight). Singularity reaches 1100 then.
Singularity (E) [wiki, data; m]: the black hole 0.5 s after the cast for 5 s; enemies in it (by centre) get
  AurelionSolEDebuff (c6b14201, type 3) while inside; every script update from +0.167 [m: 0.267 apart, 19 ticks] (10 - 30 +
  12 % AP) x 0.25 to enemies it touches; enemies are dragged to the centre (champions 150 / s, others 300 / s and held
  [data StartingGravity, NonChampGravity; m: their 61s at speed 0]); in the centre below 5 % + 0.026 % x Stardust of
  their health (epic monsters not) executed (true, AurelionSolE). One update after its end [m: +0.255]: 1 Stardust per
  full second each champion was in it, 2 per champion / epic / large minion / large monster killed in it, 1 for others.
  [open] a once-per-target tick named AurelionSolPassive (2.4 % of its hits) whose rule is not known: not sent.
Falling Star (R) [wiki, data; m]: at +1.269 [m] 150 / 250 / 350 + 75 % AP (AurelionSolRMissile) in its radius, stunned
  1 s (AurelionSolRVacuumBlast and the plain stun beab0700 [m]), 5 Stardust per champion hit. From its learning,
  AurelionSolRManager (f2dcf60d) counts the Stardust gained (430); at 75: AurelionSolRAnnouncement (e4483606), the
  manager off and the slot The Skies Descend (78) [m]. The Skies Descend (R2): at +2.011 [m] 125 % (AurelionSolR2Missile) in
  sqrt(388.91^2 + 21.85^2 x S) [wiki], knocked up 1 s (7606d40f, type 30), 5 Stardust per champion [a: as Falling Star];
  then a shockwave to 5000 over 3 s: champions and epic monsters 90 % of Falling Star's damage (AurelionSolR2Shockwave),
  every enemy it meets slowed 50 % 1 s (38e11308) and revealed 1.5 s - not the ones the star hit; the slot back to
  Falling Star, the announcement off, the manager again from 0.
"""
import math

from . import Kit
from .. import packets as P
from ..units import dist
from ..game import SCRIPT_UPDATE

STARDUST, RMANAGER, ANNOUNCE = P.elf('AurelionSolPassive'), P.elf('AurelionSolRManager'), P.elf('AurelionSolRAnnouncement')
QBUFF, QDEBUFF, QFLIGHT = P.elf('AurelionSolQ'), P.elf('AurelionSolQDebuff'), Kit.h('3e912a06')
WBUFF, EDEBUFF = P.elf('AurelionSolW'), P.elf('AurelionSolEDebuff')
RSTUN, STUN = P.elf('AurelionSolRVacuumBlast'), Kit.h('beab0700')
KNOCKUP, WAVE_SLOW = P.elf('AurelionSolR2KnockupDebuff'), P.elf('AurelionSolR2ShockwavePush')
SKIP_BUFFS = {P.u32(h) for h in (STARDUST, RMANAGER, ANNOUNCE, QBUFF, QDEBUFF, QFLIGHT, WBUFF, EDEBUFF, RSTUN, STUN, KNOCKUP,
                                   WAVE_SLOW)}
SKIP_SLOTS = ('AurelionSolW', 'AurelionSolR', 'AurelionSolR2')
SLOTS = {'AurelionSolQ': 0, 'AurelionSolW': 1, 'AurelionSolE': 2, 'AurelionSolR': 3, 'AurelionSolR2': 3}
TICK = 0.1                               # [m] Breath of Light's tick (data mChargeUpdateInterval)
SPLASH = 250.0                           # [m] its secondary targets around the first
DT = 1.0 / 30.0


def lerp(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


class AurelionSol(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stardust = 0
        self.started = False
        self.r_learnt = False
        self.calamity = 0
        self.r2_ready = False
        self.q = None                    # the channel
        self.fly = None                  # the flight
        self.hole = None                 # the black hole
        self.waves = []                  # The Skies Descend's shockwaves
        self.hurt = {}                   # enemy champion net -> when he last damaged it
        self.w_cut = 0                   # takedowns during the flight: their cut waits for its end
        self.frame = 0

    def dv(self, spell, name, rank=None):
        from ..spells import info
        r = self.hero.spell_levels[SLOTS[spell]] if rank is None else rank
        return info(self.hero.champ, spell).data_value((name,), r) or 0.0

    def inf(self, name='AurelionSolQ'):
        from ..spells import info
        return info(self.hero.champ, name)

    def take(self, u, key):
        g = self.g
        b = getattr(u, 'buff_list', {}).pop(key, None)
        if b is not None and b.get('known', True):
            g.tell_all(g.pk.buff_remove(u.net, b['slot'], b['hash']))

    def counter(self, key, h, n):
        g, hero = self.g, self.hero
        b = getattr(hero, 'buff_list', {}).get(key)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], h, n)

    def slot(self, slot, name):
        g, hero = self.g, self.hero
        hero.slot_names[slot] = name
        g.q += g.pk.spell_in_slot(hero.net, slot, name)

    # ------------------------------------------------------------------ Stardust
    def gain(self, n):
        g, hero = self.g, self.hero
        self.stardust += n
        self.counter(('kit', 'asol_stardust'), STARDUST, self.stardust)
        if self.r_learnt and not self.r2_ready:
            self.calamity += n
            self.counter(('kit', 'asol_rmanager'), RMANAGER, self.calamity)
            if self.calamity >= (self.dv('AurelionSolR', 'CalamityStacks') or 75):
                self.r2_ready = True
                g.spells.buff(hero, hero, self.inf('AurelionSolR'), 1, 25000.0, key=('kit', 'asol_announce'), name_hash=ANNOUNCE)
                self.take(hero, ('kit', 'asol_rmanager'))
                self.slot(3, 'AurelionSolR2')

    def r_manager(self):
        g, hero = self.g, self.hero
        self.calamity = 0
        g.spells.buff(hero, hero, self.inf('AurelionSolR'), 1, 25000.0, key=('kit', 'asol_rmanager'), name_hash=RMANAGER)

    def outer(self):
        return math.sqrt(275.0 ** 2 + 900.0 / math.pi * self.stardust)

    # ------------------------------------------------------------------ ranges
    def cast_range(self, hero, inf, rank):
        if inf.name == 'AurelionSolE' and self.fly is not None:
            return self.dv('AurelionSolW', 'OverrideECastRange') or 1100.0
        if inf.name in ('AurelionSolQ', 'AurelionSolE'):
            return lerp(750.0, 920.0, hero.level)        # [wiki] by level
        return None

    # ------------------------------------------------------------------ casts
    def cast_cooldown(self, hero, inf, rank, cd):
        if inf.name in ('AurelionSolQ', 'AurelionSolE'):
            return 0.0                                   # [m: their casts' 1215 carry 0; a 635 when they end]
        return None

    def cast_request(self, hero, slot, aim, target):
        g = self.g
        if slot == 0 and self.q is not None:
            self.q_end()
            return f'{hero.name} ends Breath of Light'
        if slot == 1 and self.fly is not None:
            if g.t - self.fly['t0'] >= 0.5:
                self.w_end()
                return f'{hero.name} ends Astral Flight'
            return f'{hero.name}: Astral Flight cannot be recast yet'
        if self.q is not None and slot in (1, 2, 3):
            self.q_end()                                 # [wiki] another ability ends the channel
        return None

    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'AurelionSolQ':
            self.q_start(c)
        elif name == 'AurelionSolW':
            c['kit_dash'] = True
            hero.cooldowns[0] = g.t                      # [wiki] it resets Breath of Light
            hero.refresh_bits()
            g.at(g.t + 0.401, lambda t: hero.alive and g.spells.buff(hero, hero, self.inf('AurelionSolW'), 2, 4.0,
                                                                      key=('kit', 'asol_w'), name_hash=WBUFF))
            g.at(g.t + 0.434, lambda t, c=c: self.w_start(c))
        elif name == 'AurelionSolE':
            g.at(g.t + 0.001, lambda t: hero.cooldowns.__setitem__(2, t + 30.0))      # held until the black hole ends
            g.at(g.t + 0.501, lambda t, c=c: self.e_form(c) if hero.alive else self.e_cooldown())
        elif name == 'AurelionSolR':
            g.at(g.t + 1.269, lambda t, c=c: self.r_impact(c, False))
        elif name == 'AurelionSolR2':
            g.at(g.t + 2.011, lambda t, c=c: self.r_impact(c, True))

    def resolve(self, c):
        return c['inf'].name in SLOTS

    def spell_hit(self, c, tgt):
        return True                                      # every hit of his is the kit's (the templates' missiles land too)

    def order(self, hero, kind, arg):
        if self.fly is not None:
            return True                                  # [a] the flight goes on: orders are not taken during it
        if self.q is not None:
            self.q_end()                                 # [wiki] moving or attacking ends the channel
        return None

    def skip_template(self, e):
        v = e.get('values') if isinstance(e.get('values'), dict) else {}
        pid = e['pid']
        if pid == 435 and v.get('+0x64') in SKIP_BUFFS:
            return True
        if pid == 262 and v.get('+0x14') in SKIP_BUFFS:
            return True
        if pid == 1140:
            return True                                  # the flight is the kit's
        if pid == 635:
            return True                                  # [m] Q's and E's start when they end, W's 15 s at the start: the kit's
        if pid == 78:
            txt = (v.get('+0x20') or {}).get('text') if isinstance(v.get('+0x20'), dict) else None
            try:
                name = bytes.fromhex(txt).rstrip(b'\0').decode() if txt else ''
            except ValueError:
                name = ''
            if name in SKIP_SLOTS:
                return True
        return False

    # ------------------------------------------------------------------ Breath of Light
    def q_start(self, c):
        g, hero = self.g, self.hero
        tgt = c['tgt']
        if tgt is None:
            near = [o for o in g.spells.enemies(hero) if o.is_hero and dist(o.pos, c['aim']) <= 300.0]
            tgt = min(near, key=lambda o: dist(o.pos, c['aim'])) if near else None
        self.q = {'t0': g.t, 'dir': c['direction'], 'tgt': tgt, 'next': g.t + 2.0 / 30.0, 'mana_at': g.t + 0.25,
                  'timers': {}, 'hit': set()}
        q = self.q

        def buffs(t):
            if self.q is not q:
                return
            g.spells.buff(hero, hero, self.inf(), 2, 100.0, key=('kit', 'asol_q'), name_hash=QBUFF)
            if self.fly is not None:
                g.spells.buff(hero, hero, self.inf(), 2, 100.0, key=('kit', 'asol_qw'), name_hash=QFLIGHT)
        g.at(g.t + 0.033, buffs)

    def q_tick(self, t):
        g, hero = self.g, self.hero
        q = self.q
        if not hero.alive or t < hero.cc_until or t < getattr(hero, 'silence_until', 0.0):
            return self.q_end()
        if self.fly is None and hero.path:
            return self.q_end()
        hero.attack_ready = max(hero.attack_ready, t + 0.1)
        if self.fly is None and t - q['t0'] >= self.dv('AurelionSolQ', 'MaxChannelDuration') - 1e-6:
            return self.q_end()
        while t >= q['mana_at'] - 1e-6:
            cost = self.dv('AurelionSolQ', 'ManaCostPerSecond') / 4.0
            if hero.par < cost:
                return self.q_end()
            hero.set_par(hero.par - cost)
            q['mana_at'] += 0.25
        tgt = q['tgt']
        if tgt is not None and tgt.alive and dist(tgt.pos, hero.pos) > 1.0:
            want = math.atan2(tgt.pos[1] - hero.pos[1], tgt.pos[0] - hero.pos[0])
            have = math.atan2(q['dir'][1], q['dir'][0])
            turn = (want - have + math.pi) % (2.0 * math.pi) - math.pi
            step = math.radians(self.dv('AurelionSolQ', 'AngularDegreesPerSec') or 180.0) * DT
            have += max(-step, min(step, turn))
            q['dir'] = (math.cos(have), math.sin(have))
            hero.facing = q['dir']
        while t >= q['next'] - 1e-6 and self.q is q:
            self.q_hit(t)
            q['next'] += TICK

    def q_hit(self, t):
        g, hero = self.g, self.hero
        q = self.q
        d = q['dir']
        length = lerp(750.0, 920.0, hero.level)
        half = (self.dv('AurelionSolQ', 'BeamWidth') or 140.0) / 2.0
        best = None
        for o in g.spells.enemies(hero):
            rel = (o.pos[0] - hero.pos[0], o.pos[1] - hero.pos[1])
            f = rel[0] * d[0] + rel[1] * d[1]
            s = abs(-rel[0] * d[1] + rel[1] * d[0])
            if -o.radius <= f <= length + o.radius and s <= half + o.radius and (best is None or f < best[0]):
                best = (f, o)
        if best is None:
            return
        prim = best[1]
        per = (self.dv('AurelionSolQ', 'RankDamagePerSecond') + self.dv('AurelionSolQ', 'APPerSecond') * hero.ap) * TICK
        if self.fly is not None:
            per *= 1.0 + self.dv('AurelionSolW', 'TrueDamageBonus')
        tm = q['timers'].get(prim.net)
        if tm is None or t - tm['last'] > 1.0 + TICK:
            tm = q['timers'][prim.net] = {'acc': 0.0, 'last': t}
        else:
            tm['acc'] += TICK
            tm['last'] = t
        if tm['acc'] >= 1.0 - 1e-6:
            tm['acc'] = 0.0
            self.q_burst(prim)
        prim.reveal_until = max(prim.reveal_until, t + 0.25)
        targets = [(prim, 1.0)] + [(o, self.dv('AurelionSolQ', 'AOEModifier') or 0.5) for o in g.spells.enemies(hero)
                                   if o is not prim and dist(o.pos, prim.pos) <= SPLASH + o.radius]
        for o, k in targets:
            if not o.alive:
                continue
            if o.net not in q['hit']:
                q['hit'].add(o.net)
                g.spells.buff(hero, o, self.inf(), 3, 10.0, key=('kit', 'asol_qd'), name_hash=QDEBUFF)
            g.deal(hero, o, per * k, P.MAGIC, basic=False, source=P.SRC_PERIODIC, spell_hash=QBUFF)

    def q_burst(self, o):
        g, hero = self.g, self.hero
        g.deal(hero, o, self.dv('AurelionSolQ', 'RankBurstDamage') + (self.dv('AurelionSolQ', 'BurstAPRatio') or 0.3) * hero.ap,
               P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=QBUFF)
        part = self.dv('AurelionSolQ', 'QMaxHealthTrueDamagePerStack') * self.stardust * o.max_hp
        if o.kind == 'monster':
            part = min(part, self.dv('AurelionSolQ', 'MonsterDamageCap') or 300.0)
        if part > 0 and o.alive:
            g.deal(hero, o, part, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=QBUFF)
        if o.alive:
            g.spells.buff(hero, o, self.inf(), 3, 10.0, key=('kit', 'asol_qd'), name_hash=QDEBUFF)
        if o.is_hero:
            self.gain(int(self.dv('AurelionSolQ', 'QMassStolen') or 2))

    def q_end(self):
        g, hero = self.g, self.hero
        q, self.q = self.q, None
        if q is None:
            return
        self.take(hero, ('kit', 'asol_q'))
        self.take(hero, ('kit', 'asol_qw'))
        if self.fly is not None:
            cd = 0.0                                     # [wiki] no cooldown during the flight
        elif g.t - q['t0'] < 0.25:
            cd = 1.0                                     # [wiki] a lockout, no cooldown
        else:
            cd = self.inf().cooldown(hero.spell_levels[0]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        hero.cooldowns[0] = g.t + cd
        g.q += g.pk.cooldown(hero.net, 0, cd)
        hero.refresh_bits()

    # ------------------------------------------------------------------ Astral Flight
    def w_start(self, c):
        g, hero = self.g, self.hero
        if not hero.alive or g.t < hero.cc_until or g.t < hero.root_until:
            self.take(hero, ('kit', 'asol_w'))
            return self.w_back()
        d = c['direction']
        length = self.inf('AurelionSolW').range(hero.spell_levels[1]) + (self.dv('AurelionSolW', 'DistancePerMass') or 7.5) * self.stardust
        dest = (min(14800.0, max(100.0, hero.pos[0] + d[0] * length)), min(14800.0, max(100.0, hero.pos[1] + d[1] * length)))
        dest = g.nav.nearest_free(*dest) or dest
        c['dash_only'] = True
        speed = self.w_speed()
        entry = [hero, dest, speed, c]
        hero.path, hero.order = None, None
        hero.dashing = True
        g.q += g.pk.dash(g.t, hero, [hero.pos, dest], speed)
        g.spells.dashes.append(entry)
        self.fly = {'t0': g.t, 'entry': entry, 'dest': dest, 'slow': self.q is not None}
        key = ('kit', 'asol_w')

        def forever(t):
            b = getattr(hero, 'buff_list', {}).get(key)
            if self.fly is not None and b is not None:
                b['until'] = t + 25000.0
                g.spells.buffs.append([b['until'], hero, key])
                if b.get('known', True):
                    g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 25000.0, 1)     # [m] its 282
        g.at(g.t + 0.2, forever)

    def w_speed(self):
        hero = self.hero
        sp = (self.dv('AurelionSolW', 'BaseMS') or 340.0) + hero.speed
        return sp * (0.5 if self.q is not None else 1.0)

    def w_end(self):
        g, hero = self.g, self.hero
        f = self.fly
        if f is None:
            return
        if self.q is not None:
            self.q_end()                                 # [wiki] the channel ends with the flight [m: 2 frames before it]
        self.fly = None
        if f['entry'] in g.spells.dashes:
            g.spells.dashes.remove(f['entry'])
            hero.stop()
        hero.dashing = False
        self.take(hero, ('kit', 'asol_w'))
        self.w_back()

    def w_back(self):
        g, hero = self.g, self.hero
        self.slot(1, 'AurelionSolW')
        held = getattr(hero, 'held_cooldowns', {}).pop(1, None)
        if held is not None:
            hero.cooldowns[1] = max(g.t, held)
        for _ in range(self.w_cut):
            self.w_cooldown_cut()
        self.w_cut = 0
        hero.refresh_bits()

    def w_cooldown_cut(self):
        g, hero = self.g, self.hero
        total = self.inf('AurelionSolW').cooldown(hero.spell_levels[1]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        hero.cooldowns[1] = max(g.t, hero.cooldowns[1] - total * (1.0 - (self.dv('AurelionSolW', 'TakedownCooldownMultiplier') or 0.1)))
        g.q += g.pk.cooldown(hero.net, 1, hero.cooldowns[1] - g.t)
        hero.refresh_bits()

    def fly_tick(self, t):
        g, hero = self.g, self.hero
        f = self.fly
        if not hero.alive or t < hero.cc_until:
            return self.w_end()                          # [wiki] knocked down by crowd control
        if f['entry'] not in g.spells.dashes:
            return self.w_end()                          # arrived
        if f['slow'] != (self.q is not None):
            f['slow'] = self.q is not None
            f['entry'][2] = self.w_speed()
            g.q += g.pk.dash(t, hero, [hero.pos, f['dest']], f['entry'][2])

    def dealt(self, hero, tgt, dealt, basic, spell_hash, source):
        if tgt.is_hero and tgt.team != hero.team:
            self.hurt[tgt.net] = self.g.t

    def takedown(self, hero, victim):
        if self.g.t - self.hurt.get(victim.net, -99.0) <= (self.dv('AurelionSolW', 'ResetWindow') or 3.0):
            if self.fly is not None:
                self.w_cut += 1
            else:
                self.w_cooldown_cut()

    # ------------------------------------------------------------------ Singularity
    def e_form(self, c):
        g = self.g
        self.e_close()
        h = self.hole = {'center': c['aim'], 't0': g.t, 'end': g.t + (self.dv('AurelionSolE', 'Duration') or 5.0),
                         'in': {}, 'secs': {}, 'kills': [], 'last': {}}
        self.e_members(g.t)

        def tick(t):
            if self.hole is not h:
                return
            self.e_tick(t)
            if t + SCRIPT_UPDATE < h['end'] + 0.02:
                g.at(t + SCRIPT_UPDATE, tick)
        g.at(g.t + 0.167, tick)
        g.at(h['end'], lambda t: self.hole is h and self.e_close())

    def e_radius(self):
        return self.outer(), self.outer() / 2.0

    def e_members(self, t):
        g, hero = self.g, self.hero
        h = self.hole
        r, _ = self.e_radius()
        inf = self.inf('AurelionSolE')
        live = set()
        for o in g.spells.enemies(hero):
            if dist(o.pos, h['center']) <= r:
                live.add(o.net)
                if o.net not in h['in']:
                    h['in'][o.net] = t
                    g.spells.buff(hero, o, inf, 3, 1000.0, key=('kit', 'asol_e'), name_hash=EDEBUFF)
        for net in [n for n in h['in'] if n not in live]:
            self.e_leave(net, t)

    def e_leave(self, net, t):
        h = self.hole
        since = h['in'].pop(net)
        o = self.g.units.get(net)
        if o is not None:
            if o.is_hero:
                h['secs'][net] = h['secs'].get(net, 0.0) + (t - since)
            self.take(o, ('kit', 'asol_e'))

    def e_pull(self, t):
        g = self.g
        h = self.hole
        c = h['center']
        self.frame += 1
        tell = self.frame % 3 == 0
        for net in list(h['in']):
            o = g.units.get(net)
            if o is None or not o.alive or getattr(o, 'dashing', False):
                continue
            d = dist(o.pos, c)
            pull = (self.dv('AurelionSolE', 'StartingGravity') or 150.0) if o.is_hero else \
                (self.dv('AurelionSolE', 'NonChampGravity') or 300.0)
            prev = o.pos
            if d > 1.0:
                step = min(d, pull * DT)
                o.pos = (o.pos[0] + (c[0] - o.pos[0]) / d * step, o.pos[1] + (c[1] - o.pos[1]) / d * step)
            if not o.is_hero:
                o.root_until = max(o.root_until, t + 0.05)     # [wiki] minions and monsters: speed 0
                o.path = None
                if tell:
                    g.q_moves.append(g.pk.move_entry(o.net, [o.pos, prev], 0.0))
            elif tell and d > 1.0:
                g.q_moves.append(g.pk.move_entry(o.net, [o.pos] + list(o.path or []), o.speed))

    def e_tick(self, t):
        g, hero = self.g, self.hero
        h = self.hole
        r, inner = self.e_radius()
        per = (self.dv('AurelionSolE', 'BaseDamagePerSecond') + self.dv('AurelionSolE', 'DamageperSecondAPRatio') * hero.ap) * 0.25
        thr = (self.dv('AurelionSolE', 'BaseExecutionThreshold') or 5.0) / 100.0 + \
            self.dv('AurelionSolE', 'ExecutionGrowthPerBreakpoint') / 100.0 * self.stardust
        name = P.elf('AurelionSolE')
        for o in g.spells.enemies(hero):
            d = dist(o.pos, h['center'])
            if d <= r + o.radius:
                g.deal(hero, o, per, P.MAGIC, basic=False, source=P.SRC_PERIODIC, spell_hash=name)
            if o.alive and d <= inner and o.hp < thr * o.max_hp and not self.epic(o):
                g.deal(hero, o, o.hp + 1.0, P.TRUE, basic=False, source=P.SRC_DIRECT, spell_hash=name)

    @staticmethod
    def epic(u):
        from ..tooltips import EPIC_MONSTERS
        return u.kind == 'monster' and any(k in u.name for k in EPIC_MONSTERS)

    @staticmethod
    def large(u):
        from ..tooltips import LARGE_MONSTERS
        if u.kind == 'minion':
            return getattr(u, 'mtype', 0) in (6, 7)      # siege, super
        return u.kind == 'monster' and any(u.name.startswith(k) for k in LARGE_MONSTERS)

    def e_close(self):
        g = self.g
        h, t = self.hole, g.t
        if h is None:
            return
        for net in list(h['in']):
            self.e_leave(net, t)
        self.hole = None
        g.at(h['t0'] + 5.131, lambda t2: self.e_cooldown())      # [m: the 635 0.131 s after it ends]
        gains = [1] * sum(int(s + 1e-6) for s in h['secs'].values()) + h['kills']

        def grant(t2):
            for n in gains:
                self.gain(n)
        if gains:
            g.at(t + 0.255, grant)                       # [m] one script update after its end

    def e_cooldown(self):
        g, hero = self.g, self.hero
        cd = self.inf('AurelionSolE').cooldown(hero.spell_levels[2]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        hero.cooldowns[2] = g.t + cd
        g.q += g.pk.cooldown(hero.net, 2, cd)
        hero.refresh_bits()

    def any_unit_death(self, me, u, killer):
        h = self.hole
        if h is not None and u.net in h['in'] and u.team != self.hero.team:
            h['kills'].append(2 if self.large(u) or self.epic(u) else 1)
            self.e_leave(u.net, self.g.t)

    def any_death(self, me, victim, credit):
        h = self.hole
        if h is not None and victim.net in h['in'] and victim.team != self.hero.team:
            h['kills'].append(2)
            self.e_leave(victim.net, self.g.t)

    # ------------------------------------------------------------------ Falling Star / The Skies Descend
    def r_impact(self, c, skies):
        g, hero = self.g, self.hero
        rank = hero.spell_levels[3]
        base = self.dv('AurelionSolR', 'BaseDamage', rank) + (self.dv('AurelionSolR', 'APRatio', rank) or 0.75) * hero.ap
        inf = self.inf('AurelionSolR')
        center = c['aim']
        if skies:
            radius = math.sqrt(388.91 ** 2 + 21.85 ** 2 * self.stardust)
            amount, name = base * (self.dv('AurelionSolR', 'R2DamageRatio', rank) or 1.25), P.elf('AurelionSolR2Missile')
        else:
            radius = self.outer()
            amount, name = base, P.elf('AurelionSolRMissile')
        hit = set()
        for o in g.spells.enemies(hero):
            if dist(o.pos, center) <= radius + o.radius:
                hit.add(o.net)
                g.deal(hero, o, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=name)
                if o.alive:
                    if skies:
                        g.spells.cc(hero, o, inf, 30, 1.0, stun=True, name_hash=KNOCKUP)
                    else:
                        g.spells.cc(hero, o, inf, 5, self.dv('AurelionSolR', 'StunDuration', rank) or 1.0, stun=True, name_hash=RSTUN)
                        g.spells.cc(hero, o, inf, 5, self.dv('AurelionSolR', 'StunDuration', rank) or 1.0, stun=True, name_hash=STUN)
                if o.is_hero:
                    self.gain(int(self.dv('AurelionSolR', 'MassStolen', rank) or 5))
        if skies:
            self.waves.append({'center': center, 't0': g.t, 'r0': radius, 'met': hit,
                               'amount': base * (self.dv('AurelionSolR', 'ShockwaveDamageRatio', rank) or 0.9)})
            self.r2_ready = False
            self.take(hero, ('kit', 'asol_announce'))
            self.slot(3, 'AurelionSolR')
            g.at(g.t + 0.033, lambda t: self.r_manager())

    def wave_tick(self, t):
        g, hero = self.g, self.hero
        keep = []
        inf = self.inf('AurelionSolR')
        for w in self.waves:
            k = min(1.0, (t - w['t0']) / 3.0)
            front = w['r0'] + (5000.0 - w['r0']) * k
            for o in g.spells.enemies(hero):
                if o.net in w['met'] or dist(o.pos, w['center']) > front + o.radius:
                    continue
                w['met'].add(o.net)
                if o.is_hero or self.epic(o):
                    g.deal(hero, o, w['amount'], P.MAGIC, basic=False, source=P.SRC_DIRECT,
                           spell_hash=P.elf('AurelionSolR2Shockwave'))
                if o.alive:
                    g.spells.slow(hero, o, inf, self.dv('AurelionSolR', 'ShockwaveSlow') or 0.5, 1.0, name_hash=WAVE_SLOW)
                    o.reveal_until = max(o.reveal_until, t + 1.5)
            if k < 1.0:
                keep.append(w)
        self.waves = keep

    # ------------------------------------------------------------------ every frame
    def tick(self, hero, t):
        g = self.g
        if not self.started:
            self.started = True
            if t < 1.0:                                  # [wiki; m: 635 slot 1, 15 s at 0:00] no flight in the first 15 s
                hero.cooldowns[1] = t + 15.0
                g.q += g.pk.cooldown(hero.net, 1, 15.0)
            g.spells.buff(hero, hero, self.inf(), 1, 25000.0, key=('kit', 'asol_stardust'),
                          name_hash=STARDUST)
        if not self.r_learnt and hero.spell_levels[3] > 0:
            self.r_learnt = True
            self.r_manager()
        if self.q is not None:
            self.q_tick(t)
        if self.fly is not None:
            self.fly_tick(t)
        if self.hole is not None:
            self.e_members(t)
            if self.hole is not None:
                self.e_pull(t)
        if self.waves:
            self.wave_tick(t)

    def died(self, hero):
        if self.q is not None:
            self.q_end()
        if self.fly is not None:
            self.w_end()


KIT = AurelionSol
