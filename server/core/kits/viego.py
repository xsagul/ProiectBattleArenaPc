"""Viego - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Blade of the Ruined King's passive [wiki V26.x; m: replay 4012290107 - its own 150 named 00000000 in the attack's frame
before the attack's damage]: basic attacks deal 2 / 3 / 4 / 5 / 6 % (by Q rank) of the target's current health as bonus
physical damage, at least 10 / 15 / 20 / 25 / 30, at most 80 against monsters.
"""
from . import Kit
from .. import packets as P

PCT = [0.02, 0.03, 0.04, 0.05, 0.06]
LOW = [10.0, 15.0, 20.0, 25.0, 30.0]


class Viego(Kit):
    def attack_hit(self, hero, tgt, amount):
        rank = hero.spell_levels[0]
        if rank >= 1 and tgt.alive and not tgt.is_structure:
            bonus = max(LOW[rank - 1], PCT[rank - 1] * tgt.hp)
            if tgt.kind == 'monster':
                bonus = min(80.0, bonus)
            self.g.deal(hero, tgt, bonus, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=0)
        return amount


KIT = Viego
