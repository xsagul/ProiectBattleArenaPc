"""Ahri, the Nine-Tailed Fox - the live wiki (V26.06, = the 16.20 data) checked against the replays.

Essence Theft (P) [wiki + data AhriPassive]: a stack per minion / monster she kills (AhriPassiveCounter, type 1: given at
  the first, then a 282 with the count at each); at 9 they are consumed: heal 35 - 95 (by level) + 20 % AP, the counter
  ends (262) and a 78 puts AhriPassive in slot 0x35 [m: replays]. A champion takedown within 3 s (TakedownWindow) of
  damaging it: heal 75 - 165 + 30 % AP, a 78 puts AhriPassiveMissile in slot 0x34 [m]; while Spirit Rush's recast
  window is open it is extended to at least 10 s and gains a recast (up to 3 stored).
Orb of Deception (Q) [wiki, data]: the orb's flight is the templates' (AhriQMissile out, AhriQReturnMissile back);
  each pass hits a unit once: 35 - 135 + 50 % AP, magic out, TRUE back, both named AhriQ [m: replays' 150 types].
Fox-Fire (W) [wiki, data]: + 40 % move speed decaying over 2 s; three flames, aimed 0.25 s after the cast at priority
  targets within 725 (champions charmed by her, champions, minions this flame kills, her last attack's target within
  3 s), else at 0.4 s at the closest enemy within 550; they leave at 0.401 s [m: template] and hit on arrival:
  40 - 120 + 40 % AP, 40 % for a flame after the first on the same unit, x 2 against minions under 20 % health.
  [m: 117 of 135 casts with a champion hit put all three on it; minions get one each while it kills them]
Charm (E) [wiki, data]: the first enemy hit: 80 - 240 + 85 % AP, charmed (f5f86700, type 23), 1edcb701 (type 3) and
  slowed 65 % (67a30700) for 1.2 - 1.8 s (CharmDuration) [m: the three with one duration].
Spirit Rush (R) [wiki, data]: the dash is the templates'; then bolts at up to 3 visible enemies within 600 (champions
  first, then the nearest), each 75 / 125 / 175 + 35 % AP (AhriRMissile). Three casts in a 15 s window, 1 s between them;
  the cooldown counts from the first cast and holds while the window is open.
Not played: the flames' orbit before they leave, Charm's knock-down of dashes.
"""
from . import Kit
from .. import packets as P
from ..units import dist

COUNTER = P.elf('AhriPassiveCounter')
CHARM, CHARM2, CHARM_SLOW = (Kit.h(x) for x in ('f5f86700', '1edcb701', '67a30700'))
W_LEAVE = 0.401


def lerp_level(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


class Ahri(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stacks = 0
        self.r_window = 0.0                  # recasts possible until then
        self.r_casts = 0
        self.r_cd_end = 0.0                  # the real cooldown's end (from the first cast)
        self.last_attack = (None, -99.0)

    def dv(self, spell, name):
        from ..spells import info
        rank = self.hero.spell_levels['QWER'.index(spell[4])]
        return info(self.hero.champ, spell).data_value((name,), rank) or 0.0

    # ------------------------------------------------------------------ Essence Theft
    def killed(self, hero, u):
        g = self.g
        if u.kind not in ('minion', 'monster'):
            return
        self.stacks += 1
        if not hasattr(hero, 'buff_list'):
            hero.buff_list = {}
        key = ('kit', 'ahri_counter')
        if self.stacks == 1:
            from ..spells import info
            g.spells.buff(hero, hero, info(hero.champ, 'AhriQ'), 1, 25000.0, key=key, name_hash=COUNTER)
            return
        b = hero.buff_list.get(key)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, 25000.0, self.stacks)
        if self.stacks >= 9:
            self.stacks = 0
            b = hero.buff_list.pop(key, None)
            if b is not None and b.get('known', True):
                g.tell_all(g.pk.buff_remove(hero.net, b['slot'], COUNTER))
            g.q += g.pk.spell_in_slot(hero.net, 0x35, 'AhriPassive')
            hero.heal(lerp_level(35.0, 95.0, hero.level) + 0.2 * hero.ap)

    def takedown(self, hero, victim):
        g = self.g
        if g.t - victim.last_hit_by.get(hero.net, -99.0) > 3.0:
            return
        g.q += g.pk.spell_in_slot(hero.net, 0x34, 'AhriPassiveMissile')
        hero.heal(lerp_level(75.0, 165.0, hero.level) + 0.3 * hero.ap)
        if g.t < self.r_window:
            self.r_window = max(self.r_window, g.t + 10.0)
            self.r_casts = max(0, self.r_casts - 1)              # one more recast (3 stored at most)

    def after_attack(self, hero, tgt, dealt):
        self.last_attack = (tgt, self.g.t)

    # ------------------------------------------------------------------ casts
    def cast_begin(self, c):
        name = c['inf'].name
        if name == 'AhriW':
            c['w_hits'] = {}
            c['targets'] = lambda c=c: self.w_targets(c)
        elif name == 'AhriR':
            c['targets'] = lambda c=c: self.r_targets(c)
            self.r_cast(c)

    def resolve(self, c):
        name = c['inf'].name
        if name == 'AhriW':
            return True                              # the flames are the templates' missiles (their hits below); the
            #                                          decaying speed is core/statbuffs.py's (the wiki's stat buffs)                              # the flames are the templates' missiles; their hits below
        if name == 'AhriR':
            return False                             # the dash is generic; the bolts are the templates' missiles
        return False

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'AhriQ':
            m = c.get('missile')
            back = m is not None and getattr(m, 'returning', False)
            amount = self.dv('AhriQ', 'BaseDamage') + 0.5 * hero.ap
            g.deal(hero, tgt, amount, P.TRUE if back else P.MAGIC, basic=False, source=P.SRC_DIRECT,
                   spell_hash=P.damage_hash('AhriQ'))
            return True
        if name == 'AhriW':
            n = c['w_hits'].get(tgt.net, 0)
            c['w_hits'][tgt.net] = n + 1
            amount = self.w_damage(tgt, n)
            g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AhriWDamageMissile'))
            return True
        if name == 'AhriE':
            from ..spells import info
            inf = info(hero.champ, 'AhriE')
            amount = self.dv('AhriE', 'BaseDamage') + 0.85 * hero.ap
            g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AhriEMissile'))
            if tgt.alive and not tgt.is_structure:
                sec = self.dv('AhriE', 'CharmDuration')
                g.spells.cc(hero, tgt, inf, 23, sec, stun=True, name_hash=CHARM)
                if tgt.is_hero and tgt.bonus.get('tenacity'):
                    sec *= 1.0 - min(0.9, tgt.bonus['tenacity'])
                g.spells.buff(hero, tgt, inf, 3, sec, key=('kit', 'ahri_e2'), name_hash=CHARM2)
                g.spells.slow(hero, tgt, inf, abs(self.dv('AhriE', 'SlowPercent')), sec, name_hash=CHARM_SLOW)
            return True
        if name == 'AhriR':
            amount = self.dv('AhriR', 'RBaseDamage') + 0.35 * hero.ap
            g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AhriRMissile'))
            return True
        return False

    # ------------------------------------------------------------------ Fox-Fire
    def w_speed(self, pct, seconds):
        g, hero = self.g, self.hero
        t0 = g.t

        def step(t):
            left = 1.0 - (t - t0) / seconds
            if left <= 0 or not hero.alive:
                hero.remove_mods(('kit', 'ahri_w_ms'))
            else:
                hero.add_mods(('kit', 'ahri_w_ms'), {'ms_pct': pct * left})
                g.at(t + 0.25, step)
            if g.spells is not None:
                g.spells.respeed(hero)
        step(t0)

    def w_damage(self, tgt, n):
        amount = self.dv('AhriW', 'BaseDamage') + 0.4 * self.hero.ap
        if n > 0:
            amount *= self.dv('AhriW', 'RepeatDamageMod') or 0.4
        if tgt.kind == 'minion' and tgt.hp < (self.dv('AhriW', 'MinionBonusDamageThreshold') or 0.2) * tgt.max_hp:
            amount *= self.dv('AhriW', 'MinionBonusDamageMultiplier') or 2.0
        return amount

    def w_targets(self, c):
        """the three flames' targets, when they leave (0.401 s): priority targets (within 725) if any - else the closest
        enemy within 550"""
        if c.get('w_done'):
            return []
        c['w_done'] = True
        g, hero = self.g, self.hero
        foes = [o for o in g.spells.enemies(hero) if g.seen_by(hero.team, o)]
        out, planned = [], {}
        for i in range(3):
            def dmg(o):
                return self.w_damage(o, planned.get(o.net, 0))
            near = [o for o in foes if dist(o.pos, hero.pos) <= 725.0 and o.alive]
            charmed = [o for o in near if o.is_hero and ('AhriE', 23, CHARM) in getattr(o, 'buff_list', {})]
            heroes = [o for o in near if o.is_hero]
            kill = [o for o in near if o.kind == 'minion' and o.hp - planned.get(('hp', o.net), 0.0) <= dmg(o) and
                    o.hp - planned.get(('hp', o.net), 0.0) > 0]
            last = self.last_attack
            mark = [last[0]] if last[0] is not None and last[0] in near and g.t - last[1] <= 3.0 else []
            pick = None
            for group in (charmed, heroes, kill, mark):
                if group:
                    pick = min(group, key=lambda o: dist(o.pos, hero.pos))
                    break
            if pick is None:
                close = [o for o in foes if dist(o.pos, hero.pos) <= 550.0 and o.alive]
                if not close:
                    break
                pick = min(close, key=lambda o: dist(o.pos, hero.pos))
            planned[('hp', pick.net)] = planned.get(('hp', pick.net), 0.0) + dmg(pick)
            planned[pick.net] = planned.get(pick.net, 0) + 1
            out.append(pick)
        return out

    # ------------------------------------------------------------------ Spirit Rush
    def r_cast(self, c):
        g, hero = self.g, self.hero
        from ..spells import info
        if g.t >= self.r_window:
            # a first cast: the window opens, the real cooldown counts from now
            self.r_window = g.t + (self.dv('AhriR', 'RRecastWindow') or 15.0)
            self.r_casts = 0
            cd = info(hero.champ, 'AhriR').cooldown(hero.spell_levels[3]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
            self.r_cd_end = g.t + cd
        self.r_casts += 1
        left = 3 - self.r_casts
        # the engine sets the full cooldown at begin(); while recasts are left only the 1 s between casts holds
        g.at(g.t + 0.001, lambda t: self.r_hold(left))

    def r_hold(self, left):
        g, hero = self.g, self.hero
        if left > 0 and g.t < self.r_window:
            hero.cooldowns[3] = g.t + (self.dv('AhriR', 'RDashCooldown') or 1.0)
        else:
            hero.cooldowns[3] = max(self.r_cd_end, g.t + 1.0)
        hero.refresh_bits()

    def r_targets(self, c):
        if c.get('r_done'):
            return []
        c['r_done'] = True
        g, hero = self.g, self.hero
        foes = [o for o in g.spells.enemies(hero) if g.seen_by(hero.team, o) and dist(o.pos, hero.pos) <= 600.0]
        foes.sort(key=lambda o: (not o.is_hero, dist(o.pos, hero.pos)))
        return foes[:int(self.dv('AhriR', 'RMaxTargetsPerCast') or 3)]

    def tick(self, hero, t):
        if self.r_window and t >= self.r_window and self.r_casts:
            # the window closed with recasts left: the real cooldown holds again
            hero.cooldowns[3] = max(hero.cooldowns[3], self.r_cd_end)
            self.r_casts = 0
            self.r_window = 0.0


KIT = Ahri
