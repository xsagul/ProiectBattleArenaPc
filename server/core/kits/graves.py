"""Graves - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

New Destiny's attack speed cap (998 S2C_UpdateAttackSpeedCapOverrides) [m: 3 replays, ~4,000 a match]: told on every
update of his script while he lives, and again at every attack he begins and every cast: {cap, 1, 0, cap} - the cap
grows with his attack speed (0.4706 at none, 0.68 at +56 %); [a] our engine's attack speed is sent as the cap.
"""
from . import Kit
from .. import packets as P


STOPPED = ('f644b684', '8b73cf22', '6838f6b2')


class Graves(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.started = False

    def tell(self, t=None):
        h = self.hero
        if not h.alive:
            return
        cap = 1.0 / max(0.05, h.attack_time())
        v = {'+0x10': P.f32(cap), '+0x14': '01', '+0x15': '00', '+0x18': P.f32(cap)}
        self.g.q.append((1, 998, h.net, self.g.pk.enc(998, v)))

    def attack_start(self, hero, tgt):
        self.tell()
        # [m: replay 4012362054] his attack's start stops three animations (280)
        for h in STOPPED:
            self.g.q.append((1, 280, hero.net, self.g.pk.enc(280, {'+0x10': '00', '+0x11': '00', '+0x14': h, '+0x18': '01'})))

    def fire(self, hero, tgt):
        """[m] his shot: the recoil spell in slot 0x38, the reload's cooldown (635 slot 0x51) and animation, then three
        more shells (78 slot 0x36 GravesBasicAttackSpread, each its own missile 938 + 743)"""
        g, pk = self.g, self.g.pk
        g.q += pk.spell_in_slot(hero.net, 0x38, 'GravesAutoAttackRecoil')
        g.q.append((1, 635, hero.net, pk.enc(635, {'+0x10': P.f32(hero.attack_time()), '+0x14': '00', '+0x18': '00000000',
                                                  '+0x1c': '00000000', '+0x20': P.f32(-1.0), '+0x24': '51'})))
        g.q.append((1, 1088, hero.net, pk.enc(1088, {'+0x10': {'text': b'GravesReloadUpper'.hex()}, '+0x20': P.f32(1.0),
                                                    '+0x24': '00', '+0x25': '00', '+0x26': '00', '+0x27': '00',
                                                    '+0x28': '00000000', '+0x2c': '00000000', '+0x30': '00', '+0x31': '00'})))
        for _ in range(3):
            g.q += pk.spell_in_slot(hero.net, 0x36, 'GravesBasicAttackSpread')
            g.q += pk.missile_launch(hero, g.new_net())

    def cast_begin(self, ctx):
        self.tell()

    def tick(self, hero, t):
        if not self.started:
            self.started = True
            self.g.script_timer(0.0, self.tell, alive=lambda: not self.g.over)


KIT = Graves
