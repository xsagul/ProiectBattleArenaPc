"""Jhin - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Whisper's fixed attack speed (998) [m: every script update]: {his attack speed, 1, 1, his attack speed} (0.625 at
level 1, growing with his levels).
"""
from . import Kit
from .. import packets as P


class Jhin(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.started = False

    def tell(self, t=None):
        h = self.hero
        if not h.alive:
            return
        speed = 1.0 / max(0.05, h.attack_time())
        v = {'+0x10': P.f32(speed), '+0x14': '01', '+0x15': '01', '+0x18': P.f32(speed)}
        self.g.q.append((1, 998, h.net, self.g.pk.enc(998, v)))

    def tick(self, hero, t):
        if not self.started:
            self.started = True
            self.g.script_timer(0.0, self.tell, alive=lambda: not self.g.over)


KIT = Jhin
