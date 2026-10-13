"""Ashe, the Frost Archer - the live wiki checked against the 16.20 data and the replays.

Frost Shot (P) [wiki]: no extra critical damage - every attack instead deals + (critical chance x 100 %) of itself;
  attacks and ability hits slow 20 - 30 % (by level) for 2 s (77810a0e, type 11) [m]; a critical strike doubles the slow,
  falling back over the first second.
Ranger's Focus (Q) [wiki, data AsheQ]: attacks give Focus (4 s, 4 at most, then one lost a second) while it is off; the
  cast needs 4: for 6 s + 20 - 60 % attack speed (the wiki's stat buff, core/statbuffs.py) and every attack a flurry of
  5 arrows (6 the first, + 20 %), together 110 - 130 % AD: the first is the attack (AsheQAttack), the others
  AsheQAttackNoOnHit [m], each with Frost; the attack timer resets.
Volley (W): the cone of arrows is generic; an enemy takes 60 - 200 + 100 % bonus AD once (VolleyAttack) and Frost -
  champions the doubled slow.
Hawkshot (E) [wiki, data]: 2 charges, one every 90 - 50 s (BaseCooldown), 835 slot 2 [a: by Amumu's 835].
Enchanted Crystal Arrow (R) [wiki, data]: from where she started, 260 wide, 1500 a second growing to 2100 [a: + 600 a
  second]; the first enemy champion: 200 / 400 / 600 + 120 % AP magic to it and the enemies within 400 (they get Frost),
  it is stunned 1 - 3.5 s by the distance flown [a: the most at 1500].
"""
from . import Kit
from .. import packets as P
from ..units import dist

FROST = Kit.h('77810a0e')
FOCUS = P.elf('AsheQ')


def lerp(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


class Ashe(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.focus, self.focus_until, self.focus_drop = 0, 0.0, 0.0
        self.q_until = 0.0
        self.q_first = False
        self.charges, self.recharge_at = None, None

    def dv(self, spell, name):
        from ..spells import info
        k = {'AsheQ': 0, 'Volley': 1, 'AsheSpiritOfTheHawk': 2, 'EnchantedCrystalArrow': 3}[spell]
        return info(self.hero.champ, spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    def inf(self):
        from ..spells import info
        return info(self.hero.champ, 'AsheQ')

    def frost(self, tgt, crit=False):
        g, hero = self.g, self.hero
        if not tgt.alive or tgt.is_structure:
            return
        pct = lerp(0.2, 0.3, hero.level)
        g.spells.slow(hero, tgt, self.inf(), pct * (2.0 if crit else 1.0), 2.0, name_hash=FROST)
        if crit:
            t0 = g.t

            def fall(t):
                if tgt.alive and self.inf().name in getattr(tgt, 'slows', {}) and t - t0 < 1.0:
                    tgt.slows[self.inf().name] = pct * (2.0 - (t - t0))
                    g.spells.respeed(tgt)
                    g.at(t + 0.1, fall)
                elif tgt.alive and self.inf().name in getattr(tgt, 'slows', {}):
                    tgt.slows[self.inf().name] = pct
                    g.spells.respeed(tgt)
            g.at(t0 + 0.1, fall)

    # ------------------------------------------------------------------ attacks
    def attack_hit(self, hero, tgt, amount):
        if hero.attack_crit:
            amount /= 1.75                               # [wiki] her critical strikes deal no more
        amount *= 1.0 + min(1.0, hero.crit)
        if self.g.t < self.q_until:
            arrows = 6 if self.q_first else 5
            per = (self.dv('AsheQ', 'DamagePerStrike') or 1.1) / 5.0 * (1.2 if self.q_first else 1.0) * 5.0 / arrows
            self.flurry = (arrows - 1, per * hero.ad * (1.0 + min(1.0, hero.crit)))
            self.q_first = False
            return per * hero.ad * (1.0 + min(1.0, hero.crit))
        self.flurry = None
        return amount

    def after_attack(self, hero, tgt, dealt):
        g = self.g
        crit = hero.attack_crit
        self.frost(tgt, crit)
        fl = getattr(self, 'flurry', None)
        if fl and tgt.alive:
            for _ in range(fl[0]):
                g.deal(hero, tgt, fl[1], P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AsheQAttackNoOnHit'))
            self.flurry = None
        elif g.t >= self.q_until:
            self.add_focus()

    def attack_override(self, hero, tgt):
        if self.g.t < self.q_until:
            hero.attack_name = 'AsheQAttack'
        return None

    def add_focus(self):
        g, hero = self.g, self.hero
        if hero.spell_levels[0] <= 0:
            return
        self.focus = min(4, self.focus + 1)
        self.focus_until = g.t + 4.0
        self.focus_drop = self.focus_until
        key = ('kit', 'ashe_focus')
        b = getattr(hero, 'buff_list', {}).get(key)
        if b is None:
            g.spells.buff(hero, hero, self.inf(), 2, 4.0, key=key, name_hash=FOCUS)
            b = hero.buff_list.get(key)
        else:
            b['until'] = self.focus_until
            g.spells.buffs.append([b['until'], hero, key])
            if b.get('known', True):
                g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 4.0, 1)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], FOCUS, self.focus)

    # ------------------------------------------------------------------ casts
    def cast_request(self, hero, slot, aim, target):
        if slot == 0 and (self.focus < 4 or self.g.t < self.q_until):
            return f'{hero.name}: Ranger\'s Focus needs 4 Focus'
        return None

    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'AsheQ':
            self.focus = 0
            b = getattr(hero, 'buff_list', {}).pop(('kit', 'ashe_focus'), None)
            if b is not None and b.get('known', True):
                g.tell_all(g.pk.buff_remove(hero.net, b['slot'], FOCUS))
            self.q_until = g.t + (self.dv('AsheQ', 'BuffDuration') or 6.0)
            self.q_first = True
            hero.attack_ready = g.t                      # the attack timer resets
        elif name == 'AsheSpiritOfTheHawk':
            if self.charges is None:
                self.charges = 2
            self.charges -= 1
            if self.recharge_at is None:
                self.recharge_at = g.t + self.dv('AsheSpiritOfTheHawk', 'BaseCooldown')
            self.ammo()
            g.at(g.t + 0.001, lambda t: self.e_cooldown())
        elif name == 'EnchantedCrystalArrow':
            self.r_fly(c)

    def resolve(self, c):
        return c['inf'].name in ('AsheQ', 'EnchantedCrystalArrow')

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        if c['inf'].name == 'Volley':
            g.deal(hero, tgt, self.dv('Volley', 'BaseDamage') + hero.bonus['ad'], P.PHYSICAL, basic=False,
                   source=P.SRC_DIRECT, spell_hash=P.elf('VolleyAttack'))
            self.frost(tgt, crit=tgt.is_hero)
            return True
        return False

    # ------------------------------------------------------------------ Hawkshot charges
    def ammo(self):
        g, hero = self.g, self.hero
        total = self.dv('AsheSpiritOfTheHawk', 'BaseCooldown') if self.charges < 2 else 0.0
        left = max(0.0, self.recharge_at - g.t) if self.recharge_at and self.charges < 2 else 0.0
        v = {'+0x10': P.u32(self.charges), '+0x14': '00', '+0x18': P.f32(total), '+0x1c': 'ffffffff', '+0x20': P.f32(left),
             '+0x24': P.u32(2)}
        g.q.append((1, 835, hero.net, g.pk.enc(835, v)))

    def e_cooldown(self):
        hero = self.hero
        hero.cooldowns[2] = self.g.t + (5.0 if self.charges > 0 else max(0.0, self.recharge_at - self.g.t))
        hero.refresh_bits()

    # ------------------------------------------------------------------ Enchanted Crystal Arrow
    def r_fly(self, c):
        g, hero = self.g, self.hero
        start = hero.pos
        d = c['direction']
        st = {'pos': start, 'speed': 1500.0, 'flown': 0.0}
        from ..spells import _point_segment

        def step(t):
            if st['flown'] > 25000.0:
                return
            stepl = st['speed'] / 30.0
            a = st['pos']
            nxt = (a[0] + d[0] * stepl, a[1] + d[1] * stepl)
            for o in g.heroes:
                if o.alive and o.team != hero.team and o.targetable and _point_segment(o.pos, a, nxt)[0] <= 130.0 + o.radius:
                    return self.r_hit(o, st['flown'])
            if not (0 <= nxt[0] <= 15000 and 0 <= nxt[1] <= 15000):
                return
            st['pos'] = nxt
            st['flown'] += stepl
            st['speed'] = min(2100.0, st['speed'] + 600.0 / 30.0)
            g.at(t + 1.0 / 30.0, step)
        g.at(g.t + 0.25, step)

    def r_hit(self, tgt, flown):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'EnchantedCrystalArrow')
        amount = self.dv('EnchantedCrystalArrow', 'RBaseDamage') + 1.2 * hero.ap
        center = tgt.pos
        for o in g.spells.enemies(hero):
            if dist(o.pos, center) <= 400.0 + o.radius:
                g.deal(hero, o, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('EnchantedCrystalArrow'))
                if o is not tgt:
                    self.frost(o)
        if tgt.alive:
            sec = 1.0 + 2.5 * min(1.0, flown / 1500.0)
            g.spells.cc(hero, tgt, inf, 5, sec, stun=True)

    def tick(self, hero, t):
        if self.focus and t >= self.focus_drop:
            self.focus -= 1
            self.focus_drop = t + 1.0
            key = ('kit', 'ashe_focus')
            b = getattr(hero, 'buff_list', {}).get(key)
            g = self.g
            if self.focus <= 0 and b is not None:
                hero.buff_list.pop(key, None)
                if b.get('known', True):
                    g.tell_all(g.pk.buff_remove(hero.net, b['slot'], FOCUS))
            elif b is not None and b.get('known', True):
                g.q += g.pk.buff_counter(hero.net, b['slot'], FOCUS, self.focus)
        if self.charges is not None and self.charges < 2 and self.recharge_at is not None and t >= self.recharge_at:
            self.charges += 1
            self.recharge_at = t + self.dv('AsheSpiritOfTheHawk', 'BaseCooldown') if self.charges < 2 else None
            self.ammo()
            if hero.cooldowns[2] > t + 5.0:
                hero.cooldowns[2] = t
                hero.refresh_bits()


KIT = Ashe
