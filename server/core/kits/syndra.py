"""Syndra - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Unleashed Power's sphere count (835, slot 3) [m: 3 replays, 40,944 packets]: from the moment R is learnt, on every
update of her script, the ammo of slot 3 = 3 + her Dark Spheres on the field (the 'Seed' units of Q / W / E), 0 while R is on cooldown; a change
is told twice in the same frame - {new, the old one} then {new, new} (the very first {new, -1}).
"""
from . import Kit
from .. import packets as P


class Syndra(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.told = None
        self.started = False

    def spheres(self):
        g, h = self.g, self.hero
        sm = getattr(g, 'summons', None)
        units = getattr(sm, 'units', []) if sm is not None else []
        return sum(1 for u in units if u.alive and u.owner is h and getattr(u, 'label', '') == 'Seed')

    def ammo(self, n, prev):
        v = {'+0x10': P.u32(n), '+0x14': '00', '+0x18': P.f32(0.0), '+0x1c': P.u32(prev & 0xffffffff),
             '+0x20': P.f32(0.0), '+0x24': P.u32(3)}
        self.g.q.append((1, 835, self.hero.net, self.g.pk.enc(835, v)))

    def update(self, t):
        h = self.hero
        if h.spell_levels[3] < 1:
            return
        n = 0 if t < h.cooldowns[3] else 3 + self.spheres()     # [m] 0 while R is on cooldown
        if n != self.told:
            self.ammo(n, -1 if self.told is None else self.told)
            self.told = n
        self.ammo(n, n)

    def tick(self, hero, t):
        if not self.started:
            self.started = True
            self.g.script_timer(0.0, self.update, alive=lambda: not self.g.over)


KIT = Syndra
