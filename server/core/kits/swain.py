"""Swain - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Ravenous Flock's soul fragments (835, slot 0x3f) [m: 2 replays, ~3,800 a match]: on every update of his script
{shown, total}; a pull of a rooted champion (SwainE2) brings a fragment: the total grows by 15 and the shown number
climbs to it by one a frame (15 packets), starting when the pull lands (0.7 - 1.5 s after the recast, 0.9 [a]).
"""
from . import Kit
from .. import packets as P

SOUL = 15
PULL_LANDS = 0.9


class Swain(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.started = False
        self.shown = 0
        self.total = 0

    def tell(self, t=None):
        v = {'+0x10': P.u32(self.shown), '+0x14': '00', '+0x18': P.f32(0.0), '+0x1c': P.u32(self.total),
             '+0x20': P.f32(0.0), '+0x24': P.u32(0x3f)}
        self.g.q.append((1, 835, self.hero.net, self.g.pk.enc(835, v)))

    def climb(self, t=None):
        if self.shown < self.total:
            self.shown += 1
            self.tell()
            self.g.after_frames(1, self.climb)

    def cast_begin(self, ctx):
        if ctx.get('name') == 'SwainE2' or getattr(ctx.get('inf'), 'name', '') == 'SwainE2':
            def land(t):
                self.total += SOUL
                self.climb()
            self.g.at(self.g.t + PULL_LANDS, land)

    def tick(self, hero, t):
        if not self.started:
            self.started = True
            self.g.script_timer(0.0, self.tell, alive=lambda: not self.g.over)


KIT = Swain
