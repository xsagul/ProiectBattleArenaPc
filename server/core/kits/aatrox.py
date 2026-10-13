"""Aatrox, the Darkin Blade - the live wiki (V26.19, = the 16.20 data's numbers) checked against the replays.

Deathbringer Stance (P) [wiki + data AatroxPassive]: ready from the start (AatroxPassiveReady, type 1); the next basic
  attack at a unit that is no structure / ward gains 50 range (PBonusAARange) and is an attack-spell (906 slot 0x2e
  AatroxPassiveAttack with its cast struct, a 78 putting AatroxPassiveAttack in slot 0x2e) [m: replays]; on hit it deals
  4 % - 10 % (by level) of the target's maximum health as magic damage named AatroxPassive (monsters: at most 100 - 320
  by level) and heals Aatrox for that post-mitigation damage (25 % against minions). Cooldown 22 - 10 s by level from
  the hit; every basic attack (not the empowered one, V14.4) or spell cast that hits at least one champion / large
  monster cuts the current cooldown by 2 s, 4 s when the Darkin Blade's sweet spot hits. On death it goes on cooldown,
  on respawn it is ready. [m] the empowered attack's damage and the bonus land in the same frame; no debuff
  (AatroxPassiveDebuff never appears).
The Darkin Blade (Q) [wiki, data AatroxQ]: hits 0.601 s after each cast [m: template]; per cast
  (QBaseDamage + QTotalADRatio x AD) x (1 + 0.25 x cast index) (+25 against monsters before the multipliers), x 1.75 in
  the sweet spot, x 55 / 60 / 65 / 70 % (levels 1 / 6 / 11 / 16) against minions.
    1st: rectangle 625 long x 180 wide in front (edge range); sweet spot: center 430 - 625 ahead
    2nd: trapezoid from 100 behind to 475 ahead, 300 -> 500 wide (edge range); sweet spot: center 260 - 475 ahead
    3rd: circle 300 around the point 200 ahead (center range); sweet spot: radius 180 (data: targeter 180)
  [m: 155 / 164 knocked-up units in the replays at their exact places (1140): the sweet spots' near edges at the 2nd
  percentile, 430 and 260 - the wiki only says "at the farthest edge"]
  Sweet spot: knocked up (9b9c080d, type 31) 0.25 s, 0.5 s for monsters. Not recast within 4 s: on cooldown then.
Infernal Chains (W) [wiki, data AatroxW]: the first enemy hit takes WBaseDamage + 40 % AD (x 2 minions) and is slowed
  25 - 35 % for 1.5 s (f72a9906); a champion / large monster is tethered (c3ea150a, type 3, 1.5 s) to where it was
  hit; still within 330 of it 1.503 s later [m: 34 tethers, the pulls' lengths 30 - 330]: the same damage again and
  pulled to that place in 0.6 s (d0119a06, type 31).
Umbral Dash (E) [wiki, data AatroxE]: the dash is generic (template); passive: heals 16 % + 1.3 % per 100 bonus health
  of the post-mitigation damage he deals to enemy champions, not from damage over time.
World Ender (R) [wiki, data AatroxR]: 10 s; enemy minions and monsters within 600 flee 3 s (b5d20600, type 29) and are
  slowed up to 99 % over it (371e2a09) [m: never champions]; + 20 / 30 / 40 % AD, + 50 / 75 / 100 % healing, bonus move
  speed 60 / 80 / 100 % losing 10 % of itself every 0.25 s; a champion takedown adds 5 s (up to 10) and unleashes the
  speed again; its attacks are the 4th / 5th variants AatroxRAttack1 / 2 (slots 0x43 / 0x44) [m: 7 : 1].
Not played: ghosting, the 5 % size, the tether's reveal, the pull ending "slightly closer to Aatrox".
"""
import math

from . import Kit
from .. import gamedata as G
from .. import packets as P
from ..units import dist

READY = P.elf('AatroxPassiveReady')
PASSIVE_DMG = P.elf('AatroxPassive')
KNOCKUP, TETHER, W_SLOW, PULL = (Kit.h(x) for x in ('9b9c080d', 'c3ea150a', 'f72a9906', 'd0119a06'))
R_FLEE, R_SLOW = Kit.h('b5d20600'), Kit.h('371e2a09')
Q_STAGE = {'AatroxQ': 0, 'AatroxQ2': 1, 'AatroxQ3': 2}
Q_HIT = 0.601
SWEET_Q1, SWEET_Q2 = 430.0, 260.0
TETHER_RANGE, PULL_TIME, TETHER_TIME = 330.0, 0.6, 1.503


def lerp_level(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


def large(u):
    return u.kind == 'monster' and 'Mini' not in u.name


# [m: 3 replays, 3,667 of Aatrox's 904s, 95 % on his passive script's updates] every script update while he lives his
# script sets his animation overrides (904, each pair twice) by his state: out of combat; in combat (5 s after damage)
# with the passive ready / not ready; World Ender (+ 7ad24b91 when the passive is ready)
ANIM_IDLE = [(0x9dd9dc06, 0x86446416), (0x2acd4eca, 0xc4010e09)]
ANIM_COMBAT_READY = [(0x9dd9dc06, 0xad818229), (0x914bd27a, 0xe86cfb58), (0x2acd4eca, 0x9cbccfd4)]
ANIM_COMBAT = [(0x9dd9dc06, 0x9c1ab75d), (0x2acd4eca, 0x82952448)]
ANIM_R = [(0x9dd9dc06, 0xffeb3beb), (0xbc9c8463, 0x7e976eab), (0x5a81bdb0, 0xada7afdb), (0x2acd4eca, 0x1ed1de36)]
ANIM_R_READY = (0x914bd27a, 0xe86cfb58)
IN_COMBAT = 5.0
# [m: 3 replays] his script's buffs renewed on every update: 33f40d0a (type 1, 1 s, from 0.25 s while he lives - gone
# for good in 1 of 3 games at 17.6 s, cause unknown) and AatroxInCombat (type 1, 5 s): given when he deals damage, 282
# at every hit and on every update while his last damage is under 5 s old, 262 after
ALIVE_BUFF, COMBAT_BUFF = 0x0a0df433, P.elf('AatroxInCombat')


class Aatrox(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.ready = False
        self.ready_at = 0.0                  # the passive comes back then
        self.empowered = None                # the target net of the empowered attack under way
        self.q_last = None                   # (time, stage) of the last Darkin Blade cast of a sequence
        self.r_until = 0.0
        self.r_speed = 0.0

    # ------------------------------------------------------------------ helpers
    def dv(self, spell, name):
        inf = self.g.spells and __import__('core.spells', fromlist=['info']).info(self.hero.champ, spell)
        rank = self.hero.spell_levels['QWER'.index({'AatroxQ': 'Q', 'AatroxW': 'W', 'AatroxE': 'E', 'AatroxR': 'R'}[spell])]
        return inf.data_value((name,), rank) or 0.0

    def ad(self):
        return self.hero.base_ad + self.hero.bonus['ad']

    def buff(self, tgt, name_hash, btype, duration, key):
        sp = self.g.spells
        from ..spells import info
        sp.buff(self.hero, tgt, info(self.hero.champ, 'AatroxQ'), btype, duration, key=key, name_hash=name_hash)

    def unbuff(self, u, key):
        b = getattr(u, 'buff_list', {}).pop(key, None)
        if b is not None and b.get('known', True):
            self.g.tell_all(self.g.pk.buff_remove(u.net, b['slot'], b['hash']))

    def charge(self, seconds):
        """Deathbringer Stance's current cooldown cut short"""
        if not self.ready:
            self.ready_at -= seconds

    # ------------------------------------------------------------------ passive
    def set_ready(self, on):
        h = self.hero
        if on == self.ready:
            return
        self.ready = on
        if on:
            self.buff(h, READY, 1, 25000.0, ('kit', 'aatrox_ready'))
            h.add_mods(('kit', 'aatrox_range'), {'range': 50.0})
        else:
            self.unbuff(h, ('kit', 'aatrox_ready'))
            h.remove_mods(('kit', 'aatrox_range'))

    def attack_override(self, hero, tgt):
        if not self.ready or tgt.is_structure or tgt.kind == 'ward':
            self.empowered = None
            return None
        self.empowered = tgt.net
        self.g.q += self.g.pk.spell_in_slot(hero.net, 0x2e, 'AatroxPassiveAttack')
        return {'slot': 0x2e, 'name': 'AatroxPassiveAttack', 'package': G.package_hash(hero.name), 'champion': hero.name}

    def attack_choices(self, hero):
        if self.g.t < self.r_until:
            return {3: 7.0, 4: 1.0}              # [m] AatroxRAttack1 / 2
        return None

    def after_attack(self, hero, tgt, dealt):
        g = self.g
        if self.empowered == tgt.net and self.ready:
            self.empowered = None
            self.set_ready(False)
            self.ready_at = g.t + lerp_level(22.0, 10.0, hero.level)
            if tgt.alive:
                amount = lerp_level(0.04, 0.10, hero.level) * tgt.max_hp
                if tgt.kind == 'monster':
                    amount = min(amount, lerp_level(100.0, 320.0, hero.level))
                got = g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=PASSIVE_DMG)
                hero.heal(got * (0.25 if tgt.kind == 'minion' else 1.0))
            return
        if tgt.is_hero or large(tgt):
            self.charge(2.0)

    def died(self, hero):
        self.set_ready(False)
        self.ready_at = 1e9
        self.r_until = 0.0
        self.r_end()

    def respawned(self, hero):
        self.set_ready(True)

    # ------------------------------------------------------------------ spells
    def resolve(self, c):
        name = c['inf'].name
        g = self.g
        if name in Q_STAGE:
            self.q_last = (c['t0'], Q_STAGE[name])
            g.at(c['t0'] + Q_HIT, lambda t, c=c: self.hero.alive and self.q_hit(c))
            return True
        if name == 'AatroxR':
            self.r_start(c)
            return True                          # its packets are the template's; its effects all the kit's
        return False

    def q_hit(self, c):
        g, hero = self.g, self.hero
        stage = Q_STAGE[c['inf'].name]
        rank = c['rank']
        d = c['direction']
        here = hero.pos
        base = self.dv('AatroxQ', 'QBaseDamage') + self.dv('AatroxQ', 'QTotalADRatio') * self.ad()
        minion_mult = 0.55 + 0.05 * sum(1 for lv in (6, 11, 16) if hero.level >= lv)
        sweet_any, big_any = False, False
        for o in g.spells.enemies(hero):
            rel = (o.pos[0] - here[0], o.pos[1] - here[1])
            f = rel[0] * d[0] + rel[1] * d[1]
            s = abs(-rel[0] * d[1] + rel[1] * d[0])
            r = o.radius
            if stage == 0:
                inside = -r <= f <= 625.0 + r and s <= 90.0 + r
                sweet = SWEET_Q1 <= f <= 625.0 and s <= 90.0
            elif stage == 1:
                half = lambda x: 150.0 + 100.0 * (min(475.0, max(-100.0, x)) + 100.0) / 575.0
                inside = -100.0 - r <= f <= 475.0 + r and s <= half(f) + r
                sweet = SWEET_Q2 <= f <= 475.0 and s <= half(f)
            else:
                cd = math.hypot(f - 200.0, s)
                inside = cd <= 300.0
                sweet = cd <= 180.0
            if not inside:
                continue
            amount = base + (self.dv('AatroxQ', 'QMonsterBonus') if o.kind == 'monster' else 0.0)
            amount *= 1.0 + 0.25 * stage
            if sweet:
                amount *= 1.0 + self.dv('AatroxQ', 'QSweetSpotBonus')
            if o.kind == 'minion':
                amount *= minion_mult
            if c.get('tpl') is not None:
                g.templates.on_cast_hit(c['tpl'], o)
            g.deal(hero, o, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash(c['inf'].name))
            if o.is_hero or large(o):
                big_any = True
                sweet_any = sweet_any or sweet
            if sweet and o.alive:
                from ..spells import info
                g.spells.cc(hero, o, info(hero.champ, c['inf'].name), 31, 0.5 if o.kind == 'monster' else 0.25, stun=True,
                            name_hash=KNOCKUP)
        if big_any:
            self.charge(4.0 if sweet_any else 2.0)

    def spell_hit(self, c, tgt):
        name = c['inf'].name
        if name == 'AatroxW':
            return self.w_hit(c, tgt)
        return False

    def w_hit(self, c, tgt):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'AatroxW')
        amount = self.dv('AatroxW', 'WBaseDamage') + self.dv('AatroxW', 'WTotalADRatio') * self.ad()
        if tgt.kind == 'minion':
            amount *= 2.0
        g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash('AatroxW'))
        if not tgt.alive:
            return True
        g.spells.slow(hero, tgt, inf, abs(self.dv('AatroxW', 'WSlowPercentage')), self.dv('AatroxW', 'WSlowDuration') or 1.5,
                      name_hash=W_SLOW)
        if tgt.is_hero or large(tgt):
            self.charge(2.0)
            center = tgt.pos
            g.at(g.t + 1.0 / 30.0, lambda t: tgt.alive and self.buff(tgt, TETHER, 3, 1.5, ('kit', 'aatrox_tether')))

            def end(t, tgt=tgt, center=center, amount=amount):
                if not (tgt.alive and hero.alive) or dist(tgt.pos, center) > TETHER_RANGE:
                    return
                g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash('AatroxW'))
                if not tgt.alive:
                    return
                g.spells.cc(hero, tgt, inf, 31, PULL_TIME, stun=True, name_hash=PULL)
                if dist(tgt.pos, center) > 5.0:
                    tgt.path = None
                    g.q += g.pk.dash(g.t, tgt, [tgt.pos, center], dist(tgt.pos, center) / PULL_TIME)

                    def arrive(t2, tgt=tgt, center=center):
                        if tgt.alive:
                            tgt.pos = center
                    g.at(g.t + PULL_TIME, arrive)
            g.at(g.t + TETHER_TIME, end)
        return True

    def own_buff(self, key, name_hash, duration, renew_only=False):
        g, h = self.g, self.hero
        if not hasattr(h, 'buff_list'):
            h.buff_list = {}
        b = h.buff_list.get(key)
        if b is None:
            if renew_only or g.spells is None:
                return
            slot = g.spells.buff_slot(h)
            b = h.buff_list[key] = {'slot': slot, 'until': g.t + duration, 'hash': name_hash, 'undo': None, 'known': True,
                                    'args': (h.net, slot, 1, name_hash, 0)}
            g.q += g.pk.buff_add(h.net, h.net, slot, 1, name_hash, duration)
        else:
            b['until'] = g.t + duration
            from ..renewals import handles
            if not handles(name_hash):
                g.q += g.pk.buff_count(h.net, b['slot'], h.net, duration, 1)
        g.spells.buffs.append([b['until'], h, key])

    def dealt(self, hero, tgt, dealt, basic, spell_hash, source=None):
        if dealt > 0 and tgt.team != hero.team:
            self.last_dealt = self.g.t
            self.own_buff(('kit', 'aatrox_combat'), COMBAT_BUFF, IN_COMBAT)
        # Umbral Dash's passive: a share of the damage to enemy champions, not of damage over time
        if tgt.is_hero and tgt.team != hero.team and dealt > 0 and source != P.SRC_PERIODIC and hero.spell_levels[2] > 0:
            bonus_hp = hero.bonus.get('hp', 0.0)
            hero.heal(dealt * (0.16 + 0.00013 * bonus_hp))

    # ------------------------------------------------------------------ World Ender
    def r_start(self, c):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'AatroxR')
        rank = c['rank']
        for o in g.spells.enemies(hero):
            if o.kind in ('minion', 'monster') and dist(o.pos, hero.pos) <= 600.0 + o.radius:
                g.spells.cc(hero, o, inf, 29, 3.0, stun=True, name_hash=R_FLEE)
                self.flee_slow(o, inf)
        self.r_until = g.t + 10.0
        hero.heal_amp = [0.5, 0.75, 1.0][min(rank, 3) - 1]
        self.r_unleash()
        hero.remove_mods(('kit', 'aatrox_r_ad'))
        hero.add_mods(('kit', 'aatrox_r_ad'), {'ad': [0.2, 0.3, 0.4][min(rank, 3) - 1] * self.ad()})
        self.r_speed_tick()

    def flee_slow(self, o, inf):
        """slowed up to 99 % over the 3 s [wiki]: the slow grows on each script update"""
        g = self.g
        g.spells.slow(self.hero, o, inf, 0.01, 3.0, name_hash=R_SLOW)
        t0 = g.t

        def step(t):
            if o.alive and t - t0 < 3.0 and inf.name in getattr(o, 'slows', {}):
                o.slows[inf.name] = min(0.99, 0.99 * (t - t0) / 3.0)
                g.spells.respeed(o)
                g.at(t + 0.25, step)
        g.at(t0 + 0.25, step)

    def r_unleash(self):
        rank = self.hero.spell_levels[3]
        self.r_speed = [0.6, 0.8, 1.0][min(max(rank, 1), 3) - 1]

    def r_speed_tick(self):
        g, hero = self.g, self.hero
        if not hero.alive or g.t >= self.r_until:
            return self.r_end()
        hero.add_mods(('kit', 'aatrox_r_ms'), {'ms_pct': self.r_speed})
        if g.spells is not None:
            g.spells.respeed(hero)
        self.r_speed *= 0.9
        g.at(g.t + 0.25, lambda t: self.r_speed_tick())

    def r_end(self):
        h = self.hero
        h.remove_mods(('kit', 'aatrox_r_ms'))
        h.remove_mods(('kit', 'aatrox_r_ad'))
        h.heal_amp = 0.0

    def takedown(self, hero, victim):
        g = self.g
        if g.t < self.r_until:
            self.r_until = min(g.t + 10.0, self.r_until + 5.0)
            self.r_unleash()

    def anim_update(self, t):
        """his passive script's update: the animation overrides of his state (904)"""
        g, h = self.g, self.hero
        if not h.alive:
            return
        fight = t - max(getattr(h, 'last_damage', -99.0), getattr(h, 'last_hurt', -99.0)) < IN_COMBAT
        if t < self.r_until:
            pairs = ANIM_R + ([ANIM_R_READY] if self.ready else [])
        elif fight:
            pairs = ANIM_COMBAT_READY if self.ready else ANIM_COMBAT
        else:
            pairs = ANIM_IDLE
        g.q += g.pk.anim_states(h.net, [p for p in pairs for _ in (0, 1)])
        self.own_buff(('kit', 'aatrox_alive'), ALIVE_BUFF, 1.0)
        if t - getattr(self, 'last_dealt', -99.0) < IN_COMBAT:
            self.own_buff(('kit', 'aatrox_combat'), COMBAT_BUFF, IN_COMBAT, renew_only=True)

    # ------------------------------------------------------------------ the frame
    def tick(self, hero, t):
        if not getattr(self, 'anim_started', False):
            self.anim_started = True
            self.g.script_timer(0.0, self.anim_update, alive=lambda: not self.g.over)
        if not hero.alive:
            return
        if not self.ready and t >= self.ready_at:
            self.set_ready(True)
        if self.q_last is not None:
            t0, stage = self.q_last
            if stage == 2 or (t - t0 > 4.0 + 0.2):
                # [wiki] the sequence is over (third cast, or not recast within 4 s): the cooldown starts then
                from ..spells import info
                inf = info(hero.champ, 'AatroxQ')
                end = t0 if stage == 2 else t0 + 4.0
                cd = inf.cooldown(hero.spell_levels[0]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
                hero.cooldowns[0] = max(hero.cooldowns[0], end + cd)
                if stage < 2:
                    self.g.q += self.g.pk.cooldown(hero.net, 0, hero.cooldowns[0] - t)
                self.q_last = None


KIT = Aatrox
