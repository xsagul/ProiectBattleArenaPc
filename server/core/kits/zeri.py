"""Zeri - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Her attack speed cap (998) [m: 3 replays, every script update]: {1.5, 1, 0, -1}; during Lightning Crash 1.6875.
"""
from . import Kit
from .. import packets as P


class Zeri(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.started = False
        self.r_until = 0.0

    def tell(self, t=None):
        h = self.hero
        if not h.alive:
            return
        cap = 1.6875 if self.g.t < self.r_until else 1.5
        v = {'+0x10': P.f32(cap), '+0x14': '01', '+0x15': '00', '+0x18': P.f32(-1.0)}
        self.g.q.append((1, 998, h.net, self.g.pk.enc(998, v)))

    def cast_begin(self, ctx):
        if getattr(ctx.get('inf'), 'name', '') == 'ZeriR':
            self.r_until = self.g.t + 10.0          # [m: 405.72 - 411.07, 541.75 - 559.68 (refreshed by takedowns)]

    def tick(self, hero, t):
        if not self.started:
            self.started = True
            self.g.script_timer(0.0, self.tell, alive=lambda: not self.g.over)


KIT = Zeri
