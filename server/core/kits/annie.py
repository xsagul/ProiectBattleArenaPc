"""Annie, the Dark Child - the live wiki checked against the 16.20 data and the replays.

Pyromania (P) [wiki; m: replays]: a stack per Disintegrate hit and per cast of her other abilities: the counter buff
  6b59ca00 (type 1, given at the first stack, then 282 with the count); at 4 it ends and Energized (b42c770c, type 1)
  is given - she starts the match (and comes back) Energized. Her next Disintegrate / Incinerate / Tibbers' summon
  stuns every enemy it hits for 1.25 / 1.5 / 1.75 s (levels 1 / 6 / 11 [a]) - two stun buffs (5ea40c0f and the plain
  stun) [m] - and ends Energized (a 1 s type-27 buff 222b5b05 follows) [m]. Death ends it all.
Disintegrate (Q): 80 - 260 + 80 % AP; a kill refunds its mana and half its cooldown.
Incinerate (W): the cone is generic; 70 - 230 + 80 % AP.
Molten Shield (E) [wiki]: herself or an allied champion (TargetOrLocation): 60 - 200 + 40 % AP shield for 3 s and 20 - 50 %
  (by level) move speed decaying over 1.5 s; enemies that damage it take 25 - 65 + 40 % AP magic, once each per cast.
Summon: Tibbers (R) [wiki]: passive 10 / 15 / 20 % magic penetration. Tibbers (the templates' unit) appears with 150 /
  275 / 400 + 75 % AP to enemies within 250 at 0.267 s [m]; his aura: 2 / 3 / 4 + 1 % AP every 0.25 s within 350; his
  attacks 30 / 45 / 60 + 10 % AP magic.
"""
from . import Kit
from .. import packets as P
from ..units import dist

STACKS, ENERGIZED, USED = Kit.h('6b59ca00'), Kit.h('b42c770c'), Kit.h('222b5b05')
STUN = Kit.h('5ea40c0f')


def lerp(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


class Annie(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stacks = 0
        self.energized = None                # set at the first tick (the match's start)
        self.cast_stun = {}                  # cast id -> True when this cast carries the stun

    def dv(self, spell, name):
        from ..spells import info
        k = {'AnnieQ': 0, 'AnnieW': 1, 'AnnieE': 2, 'AnnieR': 3}[spell]
        return info(self.hero.champ, spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    def inf(self):
        from ..spells import info
        return info(self.hero.champ, 'AnnieQ')

    def stun_time(self):
        return (1.25, 1.5, 1.75)[sum(1 for x in (6, 11) if self.hero.level >= x)]

    def take(self, key):
        g, hero = self.g, self.hero
        b = getattr(hero, 'buff_list', {}).pop(key, None)
        if b is not None and b.get('known', True):
            g.tell_all(g.pk.buff_remove(hero.net, b['slot'], b['hash']))

    def set_energized(self):
        g, hero = self.g, self.hero
        self.energized = True
        self.stacks = 0
        self.take(('kit', 'annie_stacks'))
        g.spells.buff(hero, hero, self.inf(), 1, 25000.0, key=('kit', 'annie_energized'), name_hash=ENERGIZED)

    def gain(self):
        g, hero = self.g, self.hero
        if self.energized:
            return
        self.stacks += 1
        key = ('kit', 'annie_stacks')
        if self.stacks >= 4:
            b = hero.buff_list.get(key)
            if b is not None and b.get('known', True):
                g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 25000.0, 4)
            self.set_energized()
            return
        if self.stacks == 1:
            g.spells.buff(hero, hero, self.inf(), 1, 25000.0, key=key, name_hash=STACKS)
        else:
            b = hero.buff_list.get(key)
            if b is not None and b.get('known', True):
                g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 25000.0, self.stacks)

    def use_stun(self, c):
        """this cast carries the stun: Energized ends at once"""
        g, hero = self.g, self.hero
        self.energized = False
        self.take(('kit', 'annie_energized'))
        g.spells.buff(hero, hero, self.inf(), 27, 1.0, key=('kit', 'annie_used'), name_hash=USED)
        c['pyro_stun'] = True

    def stun(self, tgt):
        g = self.g
        if tgt.alive and not tgt.is_structure:
            sec = self.stun_time()
            g.spells.cc(self.hero, tgt, self.inf(), 5, sec, stun=True, name_hash=STUN)
            g.spells.cc(self.hero, tgt, self.inf(), 5, sec, stun=True)

    # ------------------------------------------------------------------ casts
    def cast_begin(self, c):
        name = c['inf'].name
        if name in ('AnnieQ', 'AnnieW', 'AnnieR') and self.energized:
            self.use_stun(c)
        if name in ('AnnieW', 'AnnieE', 'AnnieR'):
            self.gain()
        if name == 'AnnieE':
            self.shield(c)
        elif name == 'AnnieR':
            self.g.at(self.g.t + 0.267, lambda t, c=c: self.hero.alive and self.r_burst(c))

    def resolve(self, c):
        return c['inf'].name in ('AnnieE', 'AnnieR')

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'AnnieQ':
            self.gain()
            g.deal(hero, tgt, self.dv('AnnieQ', 'BaseDamage') or (35.0 + 45.0 * hero.spell_levels[0]) + 0.8 * hero.ap,
                   P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash('AnnieQ'))
            if c.get('pyro_stun'):
                self.stun(tgt)
            if not tgt.alive:
                hero.set_par(hero.par + hero.mana_cost(0))
                hero.cooldowns[0] = g.t + max(0.0, hero.cooldowns[0] - g.t) * 0.5
                hero.refresh_bits()
            return True
        if name == 'AnnieW':
            g.deal(hero, tgt, 30.0 + 40.0 * hero.spell_levels[1] + 0.8 * hero.ap, P.MAGIC, basic=False,
                   source=P.SRC_DIRECT, spell_hash=P.damage_hash('AnnieW'))
            if c.get('pyro_stun'):
                self.stun(tgt)
            return True
        return False

    # ------------------------------------------------------------------ Molten Shield
    def shield(self, c):
        g, hero = self.g, self.hero
        tgt = c['tgt'] if c['tgt'] is not None and c['tgt'].team == hero.team and c['tgt'].is_hero else hero
        rank = hero.spell_levels[2]
        amount = 25.0 + 35.0 * rank + 0.4 * hero.ap
        tgt.shield = getattr(tgt, 'shield', {})
        tgt.shield['mAllShield'] = amount
        g.at(g.t + 3.0, lambda t: tgt.shield.pop('mAllShield', None))
        tgt.reflect = {'owner': hero, 'until': g.t + 3.0, 'hit': set(), 'amount': 15.0 + 10.0 * rank + 0.4 * hero.ap,
                       'name': P.elf('AnnieE')}
        pct = lerp(0.2, 0.5, hero.level)
        t0 = g.t

        def step(t):
            left = 1.0 - (t - t0) / 1.5
            if left <= 0 or not tgt.alive:
                tgt.remove_mods(('kit', 'annie_e_ms'))
            else:
                tgt.add_mods(('kit', 'annie_e_ms'), {'ms_pct': pct * left})
                g.at(t + 0.25, step)
            g.spells.respeed(tgt)
        step(t0)

    # ------------------------------------------------------------------ Tibbers
    def r_burst(self, c):
        g, hero = self.g, self.hero
        rank = hero.spell_levels[3]
        amount = (25.0 + 125.0 * rank) + 0.75 * hero.ap
        for o in g.spells.enemies(hero):
            if dist(o.pos, c['aim']) <= 250.0 + o.radius:
                g.deal(hero, o, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash('AnnieR'))
                if c.get('pyro_stun'):
                    self.stun(o)

    def tibbers(self):
        return next((u for u in self.g.units.values() if getattr(u, 'owner', None) is self.hero and u.alive
                     and 'Tibbers' in str(getattr(u, 'name', ''))), None)

    def tick(self, hero, t):
        g = self.g
        if self.energized is None:
            self.set_energized()                         # [wiki] Energized from the match's start
        rank = hero.spell_levels[3]
        want = (0.1, 0.15, 0.2)[rank - 1] if rank else 0.0
        if getattr(self, '_pen', None) != want:
            self._pen = want
            hero.remove_mods(('kit', 'annie_pen'))
            if want:
                hero.add_mods(('kit', 'annie_pen'), {'magic_pen_pct': want})
        if int(t * 4) != int((t - 1.0 / 30.0) * 4):
            tb = self.tibbers()
            if tb is not None:
                tb.hit_override = (15.0 * rank + 15.0 + 0.1 * hero.ap, P.MAGIC)
                for o in g.spells.enemies(hero):
                    if dist(o.pos, tb.pos) <= 350.0 + o.radius:
                        g.deal(hero, o, float(rank + 1) + 0.01 * hero.ap, P.MAGIC, basic=False, source=P.SRC_PERIODIC,
                               spell_hash=P.elf('AnnieTibbersAura'))

    def died(self, hero):
        self.stacks = 0
        self.energized = False
        self.take(('kit', 'annie_stacks'))
        self.take(('kit', 'annie_energized'))

    def respawned(self, hero):
        self.set_energized()


KIT = Annie
