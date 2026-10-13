"""Naafiri - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

We Are More's packmate count (90 S2C_UpdateSpellNumericalDisplay {slot 0x3f, number}) [m: 2 replays, ~3,450 a match]:
on every update of her script from the packmates' first spawn (~5 s) on, the number of her packmates alive (2 at rest,
4 while her spells add some, 0 after they fall).
"""
from . import Kit
from .. import packets as P


class Naafiri(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.started = False

    def packmates(self):
        sm = getattr(self.g, 'summons', None)
        return sum(1 for u in getattr(sm, 'units', []) if u.alive and u.owner is self.hero)

    def tell(self, t=None):
        v = {'+0x10': P.u32(0x3f), '+0x14': P.u32(self.packmates())}
        self.g.q.append((1, 90, self.hero.net, self.g.pk.enc(90, v)))

    def tick(self, hero, t):
        if not self.started and t >= 5.0:
            self.started = True
            self.g.script_timer(0.0, self.tell, alive=lambda: not self.g.over)


KIT = Naafiri
