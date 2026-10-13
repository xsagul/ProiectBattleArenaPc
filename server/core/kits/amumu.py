"""Amumu, the Sad Mummy - the live wiki checked against the 16.20 data (per-second values) and the replays.

Cursed Touch (P) [wiki, data AmumuP]: his basic attacks and Curse of the Sad Mummy mark enemies (AmumuPDebuff, type 3,
  3 s; Despair's ticks refresh a mark already there); a marked unit takes 10 % of every incoming pre-mitigation magic
  damage again as true damage (AmumuP, Amumu's) [m: replays - the true damage named AmumuP] - game.deal plays it.
Bandage Toss (Q) [wiki, data]: 2 charges, one every 16 / 15 / 14 / 13 / 12 s [wiki], 3 s between casts (data), told by
  835 (slot 0: charges, recharge time, time left) [m]; the bandage and the dash are the templates'; the first enemy hit
  takes 70 - 170 + 85 % AP magic and is stunned 1 s (the template's own control).
Despair (W) [wiki, data per second]: a toggle (AuraofDespair, type 1) - 8 mana a second; every 0.5 s (script timer;
  the first tick at once [m: 0.117 s]) enemies within 350 take 5 + (0.5 - 1 % + 0.25 % per 100 AP) of their maximum
  health magic (the data's per-second values halved); off again by a recast or when mana runs out.
Tantrum (E) [wiki, data]: passive: physical damage taken - (5 - 13 + 3 % bonus armor + 3 % bonus MR), at most half of
  the instance; its current cooldown - 0.75 s per basic attack he takes. The active is generic.
Curse of the Sad Mummy (R): generic (damage, snare + stun 1.5 s from the template) + the mark.
"""
from . import Kit
from .. import packets as P
from ..units import dist

CURSE = P.elf('AmumuPDebuff')
AURA = P.elf('AuraofDespair')
Q_RECHARGE = (16.0, 15.0, 14.0, 13.0, 12.0)


class Amumu(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.charges = None
        self.recharge_at = None
        self.w_on = False

    def dv(self, spell, name):
        from ..spells import info
        k = {'BandageToss': 0, 'AuraofDespair': 1, 'Tantrum': 2, 'CurseoftheSadMummy': 3}[spell]
        return info(self.hero.champ, spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    # ------------------------------------------------------------------ Cursed Touch
    def curse(self, tgt, refresh_only=False):
        g, hero = self.g, self.hero
        if not tgt.alive or tgt.is_structure or tgt.team == hero.team:
            return
        cur = getattr(tgt, 'curse', None)
        if refresh_only and (cur is None or cur[0] is not hero or g.t >= cur[1]):
            return
        tgt.curse = (hero, g.t + 3.0)
        from ..spells import info
        g.spells.buff(hero, tgt, info(hero.champ, 'BandageToss'), 3, 3.0, key=('kit', 'amumu_curse'), name_hash=CURSE)

    def after_attack(self, hero, tgt, dealt):
        self.curse(tgt)

    def dealt(self, hero, tgt, dealt, basic, spell_hash, source=None):
        if spell_hash == P.damage_hash('CurseoftheSadMummy'):
            self.curse(tgt)
        elif spell_hash == P.damage_hash('AuraofDespair'):
            self.curse(tgt, refresh_only=True)

    # ------------------------------------------------------------------ Bandage Toss charges
    def ammo(self):
        g, hero = self.g, self.hero
        left = max(0.0, (self.recharge_at or g.t) - g.t) if self.recharge_at else 0.0
        total = self.recharge_time() if self.charges < 2 else 0.0
        v = {'+0x10': P.u32(self.charges), '+0x14': '00', '+0x18': P.f32(total), '+0x1c': 'ffffffff',
             '+0x20': P.f32(left if self.charges < 2 else 0.0), '+0x24': P.u32(0)}
        g.q.append((1, 835, hero.net, g.pk.enc(835, v)))

    def recharge_time(self):
        rank = max(1, self.hero.spell_levels[0])
        return Q_RECHARGE[min(rank, 5) - 1] * 100.0 / (100.0 + self.hero.bonus.get('haste', 0.0))

    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'BandageToss':
            if self.charges is None:
                self.charges = 2
            self.charges -= 1
            if self.recharge_at is None:
                self.recharge_at = g.t + self.recharge_time()
            self.ammo()
            g.at(g.t + 0.001, lambda t: self.q_cooldown())
        elif name == 'AuraofDespair':
            if self.w_on:
                self.w_off()
            else:
                self.w_start()

    def q_cooldown(self):
        hero = self.hero
        hero.cooldowns[0] = self.g.t + (3.0 if self.charges > 0 else max(0.0, self.recharge_at - self.g.t))
        hero.refresh_bits()

    def resolve(self, c):
        return c['inf'].name == 'AuraofDespair'

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        if c['inf'].name == 'BandageToss':
            g.deal(hero, tgt, self.dv('BandageToss', 'BaseDamage') + 0.85 * hero.ap, P.MAGIC, basic=False,
                   source=P.SRC_DIRECT, spell_hash=P.damage_hash('BandageToss'))
            if tgt.alive:
                g.spells.effects(c, tgt)                 # the template's stun
            return True
        return False

    # ------------------------------------------------------------------ Despair
    def w_start(self):
        g, hero = self.g, self.hero
        from ..spells import info
        self.w_on = True
        g.spells.buff(hero, hero, info(hero.champ, 'AuraofDespair'), 1, 25000.0, key=('kit', 'amumu_w'), name_hash=AURA)

        def tick(t):
            if not self.w_on or not hero.alive:
                return
            cost = 0.5 * (self.dv('AuraofDespair', 'mana') or 8.0) if False else 4.0
            if hero.par < cost:
                return self.w_off()
            hero.set_par(hero.par - cost)
            pct = (self.dv('AuraofDespair', 'HealthDamage') / 2.0 + 0.25 * hero.ap / 100.0) / 100.0
            for o in g.spells.enemies(hero):
                if dist(o.pos, hero.pos) <= 350.0 + o.radius:
                    g.deal(hero, o, 5.0 + pct * o.max_hp, P.MAGIC, basic=False, source=P.SRC_PERIODIC,
                           spell_hash=P.damage_hash('AuraofDespair'))
        g.script_timer(0.5, tick, first=True, alive=lambda: self.w_on and hero.alive)

    def w_off(self):
        g, hero = self.g, self.hero
        self.w_on = False
        b = getattr(hero, 'buff_list', {}).pop(('kit', 'amumu_w'), None)
        if b is not None and b.get('known', True):
            g.tell_all(g.pk.buff_remove(hero.net, b['slot'], AURA))

    # ------------------------------------------------------------------ Tantrum's passive
    def incoming(self, hero, src, amount, dtype, basic):
        if hero.spell_levels[2] > 0 and dtype == P.PHYSICAL and amount > 0:
            flat = self.dv('Tantrum', 'BaseDamageReduction') + 0.03 * (hero.bonus.get('armor', 0.0) + hero.bonus.get('mr', 0.0))
            amount -= min(flat, 0.5 * amount)
        if basic and src is not None and hero.spell_levels[2] > 0:
            hero.cooldowns[2] = max(self.g.t, hero.cooldowns[2] - 0.75)
        return amount

    def tick(self, hero, t):
        if self.charges is not None and self.charges < 2 and self.recharge_at is not None and t >= self.recharge_at:
            self.charges += 1
            self.recharge_at = t + self.recharge_time() if self.charges < 2 else None
            self.ammo()
            if hero.cooldowns[0] > t + 3.0:
                hero.cooldowns[0] = t
                hero.refresh_bits()

    def died(self, hero):
        self.w_off()


KIT = Amumu
