"""Ambessa, Matriarch of War - the live wiki checked against the 16.20 data (AmbessaPassive / Q / W / E / R values win)
and the replays.

Drakehound's Step (P) [wiki, data AmbessaPassive]:
  dash - a move or attack order during an ability's lockout, or within 0.275 s after it (W: 0.25 s after its brace),
    makes her dash at the target / place when the lockout ends: 175 - 350 long, at 770 / 830 / 890 / 950 (levels 1 / 6
    / 11 / 16 [a]) + her move speed (AmbessaPassiveDash).
  Medarda Maxim - each cast adds a stack after its lockout (AmbessaPassiveAttackEmpower, type 2, 4 s, its 430 counter
    = the stacks, 3 at most, a 282 renews it) [m: replays]; each attack uses one: + 75 range, + 50 % attack speed,
    5 - 25 (by level) + 20 % bonus AD bonus physical (named like the attack: AmbessaBasicAttackChained1 / 2, her 3rd and
    4th variants) and 40 / 55 / 70 energy (levels 1 / 9 / 13 [a]).
Cunning Sweep (Q1) [wiki, data]: after 0.225 s a 180 degree cone of 400 in the aimed direction: enemies past 275 (its
  outer edge) take Damage_1_Base + 60 % bonus AD + (4 - 6 % + 3 % per 100 bonus AD) of their maximum health, the others
  half; monsters + 75 and the health part capped at 100 - 300 (by level). A hit opens Sundering Slam for 4 s
  (AmbessaQEmpowerReady, the templates').
Sundering Slam (Q2): after 0.225 s a 650 x 80 line: the first enemy full (Damage_2_Base + 90 % bonus AD + (4 - 6 % + 4 %
  per 100 bonus AD) of its maximum health), the others half; monsters as above.
Repudiation (W): a 50 - 320 (by level) + 150 % bonus AD shield for 1.5 s at the cast; after 0.5 s enemies within 325
  take BaseDamage + 50 % bonus AD, x 1.5 when the shield took damage from a champion / large monster / turret first.
Lacerate (E): after 0.225 s enemies within 325 take Damage_Flat_Base + 50 % bonus AD and are slowed 99 % decaying over
  1 s (AmbessaESlow); a dash buffered from it spins again where it ends.
Public Execution (R): passive: 10 / 20 / 30 % armor penetration; heals 15 / 17.5 / 20 % (+ 50 % of her life steal) of
  her abilities' post-mitigation damage (a quarter against minions and monsters). Active, after 0.7 s: the farthest
  enemy champion in a 1250 x 130 line - she blinks behind it, suppresses it 0.75 s (AmbessaRSuppressionDebuff, type 25;
  AmbessaRBuffSuppressing on her), then 150 / 250 / 350 + 80 % bonus AD physical and a 0.4 s stun.
"""
import math

from . import Kit
from .. import packets as P
from ..units import dist

EMPOWER = P.elf('AmbessaPassiveAttackEmpower')
E_SLOW = P.elf('AmbessaESlow')
SUPPRESS, SUPPRESSING = P.elf('AmbessaRSuppressionDebuff'), P.elf('AmbessaRBuffSuppressing')
LOCKOUT = 0.225


def lerp(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


def by_level(level, values, steps=(6, 11, 16)):
    return values[sum(1 for x in steps if level >= x)]


class Ambessa(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stacks = 0
        self.stacks_until = 0.0
        self.lockout_end = 0.0
        self.window_end = 0.0
        self.buffered = None
        self.after_dash = None               # a second Lacerate at the dash's end
        self.w = None
        self.chain = 0
        self.q2_until = 0.0
        self.q_cd_end = 0.0

    def dv(self, spell, name):
        from ..spells import info
        k = {'AmbessaQ': 0, 'AmbessaQ2': 0, 'AmbessaW': 1, 'AmbessaE': 2, 'AmbessaR': 3}[spell]
        return info(self.hero.champ, 'AmbessaQ' if spell == 'AmbessaQ2' else spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    def bad(self):
        return self.hero.bonus['ad']

    def hp_part(self, o, pct):
        v = pct * o.max_hp
        if o.kind == 'monster':
            v = min(v, lerp(100.0, 300.0, self.hero.level))
        return v

    # ------------------------------------------------------------------ Medarda Maxim
    def add_stack(self):
        g, hero = self.g, self.hero
        if not hero.alive:
            return
        from ..spells import info
        inf = info(hero.champ, 'AmbessaQ')
        key = ('kit', 'ambessa_empower')
        old = self.stacks if g.t < self.stacks_until else 0
        self.stacks = min(3, old + 1)
        self.stacks_until = g.t + 4.0
        b = getattr(hero, 'buff_list', {}).get(key)
        if b is None or old == 0:
            g.spells.buff(hero, hero, inf, 2, 4.0, key=key, name_hash=EMPOWER)
            b = hero.buff_list.get(key)
        else:
            b['until'] = self.stacks_until
            g.spells.buffs.append([b['until'], hero, key])
            if b.get('known', True):
                g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 4.0, 1)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], EMPOWER, self.stacks)
        hero.add_mods(('kit', 'ambessa_maxim'), {'range': 75.0, 'as': 0.5})

    def attack_choices(self, hero):
        if self.stacks > 0 and self.g.t < self.stacks_until:
            self.chain = 1 - self.chain
            return {2 + self.chain: 1.0}             # AmbessaBasicAttackChained1 / 2
        return None

    def after_attack(self, hero, tgt, dealt):
        g = self.g
        if self.stacks <= 0 or g.t >= self.stacks_until:
            return
        self.stacks -= 1
        key = ('kit', 'ambessa_empower')
        b = getattr(hero, 'buff_list', {}).get(key)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], EMPOWER, self.stacks)
        if self.stacks <= 0:
            b = hero.buff_list.pop(key, None)
            if b is not None and b.get('known', True):
                g.tell_all(g.pk.buff_remove(hero.net, b['slot'], EMPOWER))
            hero.remove_mods(('kit', 'ambessa_maxim'))
        if tgt.alive and not tgt.is_structure:
            g.deal(hero, tgt, lerp(5.0, 25.0, hero.level) + 0.2 * self.bad(), P.PHYSICAL, basic=False,
                   source=P.SRC_DIRECT, spell_hash=P.elf(hero.attack_name or 'AmbessaBasicAttackChained1'))
        hero.set_par(min(hero.max_par, hero.par + by_level(hero.level, (40.0, 55.0, 70.0), (9, 13))))

    # ------------------------------------------------------------------ Drakehound's Step
    def order(self, hero, kind, what):
        g = self.g
        if g.t >= self.window_end or not hero.alive or g.t < getattr(hero, 'cc_until', 0.0):
            return False
        if kind == 'attack':
            u = g.units.get(what)
            goal = u.pos if u is not None else None
        else:
            goal = what
        if goal is None:
            return False
        self.buffered = (kind, what, goal)
        delay = max(0.0, self.lockout_end - g.t)
        g.at(g.t + delay, lambda t: self.dash())
        return True

    def dash(self):
        g, hero = self.g, self.hero
        if self.buffered is None or not hero.alive:
            return
        kind, what, goal = self.buffered
        self.buffered = None
        self.window_end = 0.0
        d = dist(hero.pos, goal) or 1.0
        length = max(175.0, min(350.0, d - (100.0 if kind == 'attack' else 0.0)))
        dest = (hero.pos[0] + (goal[0] - hero.pos[0]) / d * length, hero.pos[1] + (goal[1] - hero.pos[1]) / d * length)
        dest = g.nav.nearest_free(*dest) or hero.pos
        speed = by_level(hero.level, (770.0, 830.0, 890.0, 950.0)) + hero.speed
        hero.path, hero.dashing = None, True
        g.q += g.pk.dash(g.t, hero, [hero.pos, dest], speed)
        g.q += g.pk.spell_in_slot(hero.net, 0x2e, 'AmbessaPassiveDash')
        t_end = g.t + dist(hero.pos, dest) / speed

        def land(t):
            hero.pos = dest
            hero.dashing = False
            if self.after_dash is not None and t - self.after_dash <= 1.0:
                self.after_dash = None
                self.e_spin()
            if kind == 'attack':
                hero.order_attack(what) if hasattr(hero, 'order_attack') else None
        g.at(t_end, land)

    # ------------------------------------------------------------------ casts
    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        lock = LOCKOUT
        if name == 'AmbessaW':
            lock = 0.5
            self.w = {'shield': by_level(hero.level, (50.0, 50.0, 50.0, 50.0)) if False else lerp(50.0, 320.0, hero.level)
                      + 1.5 * self.bad(), 'hit': False}
            hero.shield = getattr(hero, 'shield', {})
            hero.shield['mAllShield'] = self.w['shield']
            self.w['start'] = self.w['shield']
            g.at(g.t + 1.5, lambda t: hero.shield.pop('mAllShield', None) if self.w is None else None)
            g.at(g.t + 0.5, lambda t, c=c: self.w_smash(c))
        elif name == 'AmbessaR':
            lock = 0.7
            g.at(g.t + 0.7, lambda t, c=c: self.r_seize(c))
        elif name in ('AmbessaQ', 'AmbessaQ2'):
            if name == 'AmbessaQ2':
                # Sundering Slam: the slot back to Cunning Sweep, whose cooldown (from its cast) holds again
                c['q2'] = True
                self.q2_until = 0.0
                hero.slot_names[0] = 'AmbessaQ'
                g.at(g.t + 0.001, lambda t: self.q_restore())
            g.at(g.t + LOCKOUT, lambda t, c=c: hero.alive and self.q_hit(c))
        elif name == 'AmbessaE':
            self.after_dash = g.t
            g.at(g.t + LOCKOUT, lambda t: hero.alive and self.e_spin())
        self.lockout_end = g.t + lock
        self.window_end = self.lockout_end + (0.25 if name == 'AmbessaW' else 0.275)
        g.at(self.lockout_end, lambda t: self.add_stack())

    def resolve(self, c):
        return c['inf'].name in ('AmbessaQ', 'AmbessaQ2', 'AmbessaW', 'AmbessaE', 'AmbessaR')

    def q_hit(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        d = c['direction']
        here = hero.pos
        if c.get('q2'):
            # Sundering Slam: a line, the first enemy full
            found = []
            for o in g.spells.enemies(hero):
                rel = (o.pos[0] - here[0], o.pos[1] - here[1])
                f = rel[0] * d[0] + rel[1] * d[1]
                s = abs(-rel[0] * d[1] + rel[1] * d[0])
                if -o.radius <= f <= 650.0 + o.radius and s <= 40.0 + o.radius:
                    found.append((f, o))
            found.sort(key=lambda x: x[0])
            pct = self.dv('AmbessaQ', 'Damage_2_Percent') + 0.0004 * self.bad()
            for i, (f, o) in enumerate(found):
                amount = self.dv('AmbessaQ', 'Damage_2_Base') + 0.9 * self.bad() + self.hp_part(o, pct)
                amount += 75.0 if o.kind == 'monster' else 0.0
                amount *= 1.0 if i == 0 else 0.5
                g.deal(hero, o, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AmbessaQ2'))
            return
        pct = self.dv('AmbessaQ', 'Damage_1_Percent') + 0.0003 * self.bad()
        hits = 0
        for o in g.spells.enemies(hero):
            rel = (o.pos[0] - here[0], o.pos[1] - here[1])
            r = math.hypot(*rel)
            if r > 400.0 + o.radius or (rel[0] * d[0] + rel[1] * d[1]) < -o.radius:
                continue
            amount = self.dv('AmbessaQ', 'Damage_1_Base') + 0.6 * self.bad() + self.hp_part(o, pct)
            amount += 75.0 if o.kind == 'monster' else 0.0
            if r < 275.0:
                amount *= 0.5
            g.deal(hero, o, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AmbessaQ1'))
            hits += 1
        if hits:
            # [wiki] a hit opens Sundering Slam for 4 s (Swap_Duration), castable 0.5 s later (Swap_Static_Cooldown)
            self.q_cd_end = hero.cooldowns[0]
            self.q2_until = g.t + (self.dv('AmbessaQ', 'Swap_Duration') or 4.0)
            hero.slot_names[0] = 'AmbessaQ2'
            hero.cooldowns[0] = g.t + (self.dv('AmbessaQ', 'Swap_Static_Cooldown') or 0.5)
            hero.refresh_bits()

    def q_restore(self):
        hero = self.hero
        hero.cooldowns[0] = max(self.q_cd_end, self.g.t)
        hero.refresh_bits()

    def w_smash(self, c):
        g, hero = self.g, self.hero
        if not hero.alive or self.w is None:
            return
        took = hero.shield.get('mAllShield', 0.0) < self.w['start'] - 1e-6 and self.w.get('hit')
        amount = (self.dv('AmbessaW', 'BaseDamage') + 0.5 * self.bad()) * (1.5 if took else 1.0)
        for o in g.spells.enemies(hero):
            if dist(o.pos, hero.pos) <= 325.0 + o.radius:
                g.deal(hero, o, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AmbessaW'))
        self.w = None

    def e_spin(self):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'AmbessaE')
        amount = self.dv('AmbessaE', 'Damage_Flat_Base') + 0.5 * self.bad()
        for o in g.spells.enemies(hero):
            if dist(o.pos, hero.pos) <= 325.0 + o.radius:
                g.deal(hero, o, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AmbessaE'))
                if o.alive:
                    g.spells.slow(hero, o, inf, 0.99, 1.0, name_hash=E_SLOW)
                    t0 = g.t

                    def decay(t, o=o, t0=t0):
                        if o.alive and inf.name in getattr(o, 'slows', {}) and t - t0 < 1.0:
                            o.slows[inf.name] = 0.99 * (1.0 - (t - t0))
                            g.spells.respeed(o)
                            g.at(t + 0.1, decay)
                    g.at(t0 + 0.1, decay)

    def r_seize(self, c):
        g, hero = self.g, self.hero
        if not hero.alive:
            return
        from ..spells import info
        inf = info(hero.champ, 'AmbessaR')
        d = c['direction']
        here = hero.pos
        best = None
        for o in g.heroes:
            if not o.alive or o.team == hero.team or not o.targetable:
                continue
            rel = (o.pos[0] - here[0], o.pos[1] - here[1])
            f = rel[0] * d[0] + rel[1] * d[1]
            s = abs(-rel[0] * d[1] + rel[1] * d[0])
            if 0 <= f <= 1250.0 + o.radius and s <= 65.0 + o.radius and (best is None or f > best[0]):
                best = (f, o)
        if best is None:
            return
        tgt = best[1]
        behind = (tgt.pos[0] + d[0] * (tgt.radius + hero.radius), tgt.pos[1] + d[1] * (tgt.radius + hero.radius))
        hero.blink(g.nav.nearest_free(*behind) or tgt.pos)
        g.spells.cc(hero, tgt, inf, 25, 0.75, stun=True, name_hash=SUPPRESS)
        g.spells.buff(hero, hero, inf, 2, 0.75, key=('kit', 'ambessa_suppressing'), name_hash=SUPPRESSING)
        hero.cc_until = max(hero.cc_until, g.t + 0.75)                   # unable to act meanwhile

        def slam(t):
            if not (hero.alive and tgt.alive):
                return
            g.deal(hero, tgt, self.dv('AmbessaR', 'Damage') + 0.8 * self.bad(), P.PHYSICAL, basic=False,
                   source=P.SRC_DIRECT, spell_hash=P.elf('AmbessaR'))
            if tgt.alive:
                g.spells.cc(hero, tgt, inf, 5, 0.4, stun=True)
        g.at(g.t + 0.75, slam)

    # ------------------------------------------------------------------ Public Execution's passive
    def dealt(self, hero, tgt, dealt, basic, spell_hash, source=None):
        rank = hero.spell_levels[3]
        if rank <= 0 or basic or dealt <= 0 or tgt.team == hero.team:
            return
        pct = self.dv('AmbessaR', 'Omnivamp') + 0.5 * hero.bonus.get('lifesteal', 0.0)
        if tgt.kind in ('minion', 'monster'):
            pct *= 0.25
        hero.heal(dealt * pct)

    def tick(self, hero, t):
        if self.q2_until and t >= self.q2_until:
            self.q2_until = 0.0
            if hero.slot_names[0] == 'AmbessaQ2':
                hero.slot_names[0] = 'AmbessaQ'
            self.q_restore()
        rank = hero.spell_levels[3]
        want = self.dv('AmbessaR', 'Armor_Penetration') if rank > 0 else 0.0
        if getattr(self, '_arpen', None) != want:
            self._arpen = want
            hero.remove_mods(('kit', 'ambessa_arpen'))
            if want:
                hero.add_mods(('kit', 'ambessa_arpen'), {'armor_pen': want})
        if self.stacks and t >= self.stacks_until:
            self.stacks = 0
            hero.remove_mods(('kit', 'ambessa_maxim'))
        if self.w is not None and getattr(hero, 'last_damage', -1.0) >= t - 0.04:
            self.w['hit'] = True


KIT = Ambessa
