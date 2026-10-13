"""Anivia, the Cryophoenix - the live wiki checked against the 16.20 data and the replays.

Rebirth (P) [wiki, data RebirthMarker 240 s]: fatal damage turns her into an egg for 6 s instead (game.deal's fatal
  hook): full health, unable to act, -40 - 20 (by level) bonus armor and magic resist; alive at the end - she comes back
  with that health; killed as an egg - she dies. 240 s static cooldown.
Flash Frost (Q) [wiki, data]: an ice chunk from where she started the cast, 1100 long at 850 (data) and 220 wide:
  enemies it passes take 50 - 130 + 25 % AP (FlashFrostSpell), are slowed 20 % + 10 % per Glacial Storm rank for 3 s
  (a4fdc001) and Iced 3 s (AniviaIced, type 3). A Q pressed while it flies (cast_request), or its end, shatters it:
  enemies within 225 take 60 - 200 + 45 % AP, are stunned 1.1 - 1.5 s, Iced and slowed again.
Crystallize (W): the wall is the templates' (IceBlock units); units near it are pushed off it - champions 120,
  others 250 (a8f98b05, type 31, 0.25 s) [a: not a terrain for our pathing yet].
Frostbite (E) [wiki, data]: 55 - 155 + 55 % AP, doubled against Iced targets (the hit's moment).
Glacial Storm (R) [wiki, data]: a toggle at a place within 750 (GlacialStorm on her): 60 mana, then 35 / 45 / 55 a second;
  every 0.5 s (the first at once [m]) enemies inside take 15 / 22.5 / 30 + 6.25 % AP and are slowed 20 / 30 / 40 % for
  1 s; it grows from 200 to 400 over 1.5 s; full grown: 300 % damage, slow x 1.5 for 1.5 s, Iced. Off by a recast, mana,
  1000 away from it, or crowd control that stops casting: a last tick, then its 4 / 3 / 2 s cooldown.
"""
import math

from . import Kit
from .. import packets as P
from ..units import dist

ICED = Kit.h('b47cf10c')
CHILL = Kit.h('a4fdc001')
PUSH = Kit.h('a8f98b05')
STORM = P.elf('GlacialStorm')


class Anivia(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.ball = None                     # {'pos', 'dir', 'left', 'hit': set}
        self.storm = None                    # {'center', 't0'}
        self.egg_until = 0.0
        self.rebirth_ready = 0.0

    def dv(self, spell, name):
        from ..spells import info
        k = {'FlashFrost': 0, 'Crystallize': 1, 'Frostbite': 2, 'GlacialStorm': 3}[spell]
        return info(self.hero.champ, spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    def inf(self, name='FlashFrost'):
        from ..spells import info
        return info(self.hero.champ, name)

    def ice(self, o):
        g = self.g
        o.iced_until = g.t + 3.0
        g.spells.buff(self.hero, o, self.inf(), 3, 3.0, key=('kit', 'anivia_iced'), name_hash=ICED)

    def chill(self, o, pct, sec):
        self.g.spells.slow(self.hero, o, self.inf('GlacialStorm'), pct, sec, name_hash=CHILL)

    def q_slow(self):
        return 0.2 + 0.1 * self.hero.spell_levels[3]

    # ------------------------------------------------------------------ casts
    def cast_request(self, hero, slot, aim, target):
        if slot == 0 and self.ball is not None:
            self.shatter()
            return f'{hero.name} shatters Flash Frost'
        if slot == 3 and self.storm is not None:
            self.storm_off()
            return f'{hero.name} ends Glacial Storm'
        return None

    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'FlashFrost':
            d = c['direction']
            self.ball = {'pos': hero.pos, 'dir': d, 'left': 1100.0, 'hit': set(), 'start': g.t + 0.25}
        elif name == 'GlacialStorm':
            aim = c['aim']
            dd = dist(hero.pos, aim)
            if dd > 750.0:
                aim = (hero.pos[0] + (aim[0] - hero.pos[0]) / dd * 750.0, hero.pos[1] + (aim[1] - hero.pos[1]) / dd * 750.0)
            self.storm_on(aim)

    def resolve(self, c):
        if c['inf'].name == 'Crystallize':
            self.after_cast_wall(c)
            return False                                 # the wall's units are the templates'
        return c['inf'].name in ('FlashFrost', 'GlacialStorm')

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        if c['inf'].name == 'Frostbite':
            amount = self.dv('Frostbite', 'BaseDamage') + 0.55 * hero.ap
            if getattr(tgt, 'iced_until', 0.0) > g.t:
                amount *= 2.0
            g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('Frostbite'))
            return True
        return False

    def ball_tick(self, t):
        g, hero = self.g, self.hero
        b = self.ball
        if b is None or t < b['start']:
            return
        step = min(850.0 / 30.0, b['left'])
        a = b['pos']
        nxt = (a[0] + b['dir'][0] * step, a[1] + b['dir'][1] * step)
        from ..spells import _point_segment
        for o in g.spells.enemies(hero):
            if o.net not in b['hit'] and _point_segment(o.pos, a, nxt)[0] <= 110.0 + o.radius:
                b['hit'].add(o.net)
                g.deal(hero, o, self.dv('FlashFrost', 'PassthroughBaseDamage') + 0.25 * hero.ap, P.MAGIC, basic=False,
                       source=P.SRC_DIRECT, spell_hash=P.elf('FlashFrostSpell'))
                if o.alive:
                    self.chill(o, self.q_slow(), 3.0)
                    self.ice(o)
        b['pos'] = nxt
        b['left'] -= step
        if b['left'] <= 0.5:
            self.shatter()

    def shatter(self):
        g, hero = self.g, self.hero
        b, self.ball = self.ball, None
        if b is None:
            return
        for o in g.spells.enemies(hero):
            if dist(o.pos, b['pos']) <= 225.0 + o.radius:
                g.deal(hero, o, self.dv('FlashFrost', 'ExplosionBaseDamage') + 0.45 * hero.ap, P.MAGIC, basic=False,
                       source=P.SRC_DIRECT, spell_hash=P.elf('FlashFrostSpell'))
                if o.alive:
                    g.spells.cc(hero, o, self.inf(), 5, self.dv('FlashFrost', 'StunDuration') or 1.1, stun=True)
                    self.chill(o, self.q_slow(), 3.0)
                    self.ice(o)

    # ------------------------------------------------------------------ Crystallize's push
    def after_cast_wall(self, c):
        g, hero = self.g, self.hero
        d = c['direction']
        center = c['aim']
        half = (self.dv('Crystallize', 'WallWidth') or 600.0) / 2.0
        perp = (-d[1], d[0])
        for o in list(g.units.values()):
            if not o.alive or o.is_structure or o is hero or o.kind == 'ward':
                continue
            rel = (o.pos[0] - center[0], o.pos[1] - center[1])
            along = rel[0] * perp[0] + rel[1] * perp[1]
            across = rel[0] * d[0] + rel[1] * d[1]
            if abs(along) <= half + o.radius and abs(across) <= 100.0 + o.radius:
                push = 120.0 if o.is_hero else 250.0
                sign = 1.0 if across >= 0 else -1.0
                dest = (o.pos[0] + d[0] * sign * push, o.pos[1] + d[1] * sign * push)
                dest = g.nav.nearest_free(*dest) or o.pos
                if o.team != hero.team:
                    g.spells.cc(hero, o, self.inf('Crystallize'), 31, 0.25, stun=True, name_hash=PUSH)
                g.q += g.pk.dash(g.t, o, [o.pos, dest], push / 0.25)
                o.path = None
                o.pos = dest

    # ------------------------------------------------------------------ Glacial Storm
    def storm_on(self, center):
        g, hero = self.g, self.hero
        self.storm = {'center': center, 't0': g.t}
        g.spells.buff(hero, hero, self.inf('GlacialStorm'), 2, 25000.0, key=('kit', 'anivia_storm'), name_hash=STORM)
        self.storm_tick(g.t)
        g.script_timer(0.5, lambda t: self.storm_tick(t), first=False, alive=lambda: self.storm is not None)

    def storm_tick(self, t, last=False):
        g, hero = self.g, self.hero
        s = self.storm
        if s is None:
            return
        if not last:
            cost = 0.5 * self.dv('GlacialStorm', 'ManaCostPerSecond')
            if hero.par < cost or dist(hero.pos, s['center']) > 1000.0 or not hero.alive or t < hero.cc_until or \
                    t < getattr(hero, 'silence_until', 0.0):
                return self.storm_off()
            hero.set_par(hero.par - cost)
        grown = t - s['t0'] >= 1.5 - 1e-3
        radius = 400.0 if grown else 200.0 + 200.0 * (t - s['t0']) / 1.5
        dmg = 0.5 * self.dv('GlacialStorm', 'DamagePerSecond') + 0.0625 * hero.ap
        slow = self.dv('GlacialStorm', 'SlowAmount') / 100.0
        if grown:
            dmg *= 3.0
            slow *= 1.5
        for o in g.spells.enemies(hero):
            if dist(o.pos, s['center']) <= radius + o.radius:
                g.deal(hero, o, dmg, P.MAGIC, basic=False, source=P.SRC_PERIODIC, spell_hash=P.elf('GlacialStorm'))
                if o.alive:
                    self.chill(o, slow, 1.5 if grown else 1.0)
                    if grown:
                        self.ice(o)

    def storm_off(self):
        g, hero = self.g, self.hero
        if self.storm is None:
            return
        self.storm_tick(g.t, last=True)
        self.storm = None
        b = getattr(hero, 'buff_list', {}).pop(('kit', 'anivia_storm'), None)
        if b is not None and b.get('known', True):
            g.tell_all(g.pk.buff_remove(hero.net, b['slot'], STORM))
        cd = self.inf('GlacialStorm').cooldown(hero.spell_levels[3]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        hero.cooldowns[3] = g.t + cd
        hero.refresh_bits()

    # ------------------------------------------------------------------ Rebirth
    def fatal(self, hero, src):
        g = self.g
        if g.t < self.rebirth_ready or g.t < self.egg_until:
            return False
        self.rebirth_ready = g.t + 240.0
        self.egg_until = g.t + 6.0
        hero.set_hp(hero.max_hp)
        res = -40.0 + 60.0 * (min(18, hero.level) - 1) / 17.0
        hero.add_mods(('kit', 'anivia_egg'), {'armor': res, 'mr': res})
        hero.cc_until = max(hero.cc_until, self.egg_until)
        hero.path, hero.order, hero.target = None, None, None
        self.ball = None
        if self.storm is not None:
            self.storm_off()

        def hatch(t):
            if hero.alive:
                hero.remove_mods(('kit', 'anivia_egg'))
        g.at(self.egg_until, hatch)
        return True

    def tick(self, hero, t):
        if self.ball is not None:
            self.ball_tick(t)

    def died(self, hero):
        self.ball = None
        self.storm = None
        hero.remove_mods(('kit', 'anivia_egg'))


KIT = Anivia
