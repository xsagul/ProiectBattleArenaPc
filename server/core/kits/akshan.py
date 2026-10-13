"""Akshan, the Rogue Sentinel - the live wiki (V26.16, = the 16.20 data) checked against the replays.

Dirty Fighting (P) [wiki, data AkshanPassive]:
  second shot - 0.267 s after an attack begins [m: 127 shots, 0.267 - 0.30] the real server puts AkshanPassiveAttack in
    slot 0x32 (78) and the shot hits 0.334 s later [m: median]: 50 % AD (100 % against minions) physical, a basic attack
    (on-hit, its own critical strike), named AkshanPassiveAttack; the next attack's timer counts from it [wiki]. A move
    order before it leaves cancels it: + 20 - 75 (by level) x (1 + bonus attack speed) move speed decaying over 1 s.
  stacks - his attacks' hits and his spells' hits put AkshanPassiveDebuff on the enemy (type 3, 4.5 s - the data; a 282
    with the count 2, 3) [m]; the third consumes them: 15 / 40 / 80 / 150 (levels 1 / 6 / 11 / 16 [a]) + 60 % AP magic
    (AkshanPassive), and on a champion a 40 - 280 (level growth) + 35 % bonus AD shield for 2 s (AkshanPassiveShield),
    at most once every 16 / 12 / 8 / 4 s (levels 1 / 6 / 11 / 16 [a]) [wiki infobox; m: shortest gap 6.6 s].
Avengerang (Q) [wiki, data AkshanQ]: the boomerang is the templates' (out, back); each pass hits a unit once:
  15 - 135 + 70 % bonus AD (AkshanQMissile / AkshanQMissileReturn), non-champions x 40 - 80 % by rank; a champion hit:
  + 20 % (+ 5 % per 100 AP) move speed decaying over 1 s. [a] the range growing per enemy hit is not played.
Going Rogue (W) [wiki, data AkshanW]: camouflage while within 175 of a wall or in brush, else 2 s after leaving them; an
  attack or a cast ends it. Scoundrels: an enemy champion that kills an ally is marked 60 s (AkshanWHuntMark, type 3);
  Akshan's takedown on it within 3 s of damaging it gives 100 gold and brings back after 1 s the allies it slew.
  [a] the speed toward Scoundrels and the mana regeneration are not played.
Heroic Swing (E): generic (templates) - the swing around terrain is not played yet.
Comeuppance (R) [wiki, data AkshanR]: locked on the target for 2.5 s (the templates' packets), storing a bullet every
  0.625 / 0.521 / 0.417 s, at most 5 / 6 / 7 (all of them at a full channel); the recast (after 0.5 s, or by itself at the
  end) fires them 0.15 s apart at 3200: each (BonusDamage + 15 % AD) x (1 + 0.3 x crit chance) x (1 + 2 x missing
  health / 0.667, at most x 3), minions executed.
"""
import math

from . import Kit
from .. import gamedata as G
from .. import packets as P
from ..units import dist

DEBUFF = P.elf('AkshanPassiveDebuff')
SHIELD = P.elf('AkshanPassiveShield')
HUNT = P.elf('AkshanWHuntMark')
SECOND_AFTER, SECOND_FLIGHT = 0.267, 0.334


def by_level(level, values):
    return values[sum(1 for x in (6, 11, 16) if level >= x)]


class Akshan(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stacks = {}                     # target net -> (count, until)
        self.shield_ready = 0.0
        self.camo = None                     # {'until': t or None}
        self.scoundrels = {}                 # enemy net -> {'until': t, 'slain': [allies]}
        self.r = None

    def dv(self, spell, name):
        from ..spells import info
        k = {'AkshanQ': 0, 'AkshanW': 1, 'AkshanE': 2, 'AkshanR': 3}.get(spell)
        rank = self.hero.spell_levels[k] if k is not None else 1
        return info(self.hero.champ, spell).data_value((name,), rank) or 0.0

    # ------------------------------------------------------------------ Dirty Fighting
    def stack(self, tgt):
        g, hero = self.g, self.hero
        if not tgt.alive or tgt.is_structure or tgt.team == hero.team:
            return
        from ..spells import info
        inf = info(hero.champ, 'AkshanQ')
        n, until = self.stacks.get(tgt.net, (0, 0.0))
        n = n + 1 if g.t < until else 1
        key = ('kit', 'akshan_stack', hero.net)
        if n >= 3:
            self.stacks.pop(tgt.net, None)
            b = getattr(tgt, 'buff_list', {}).pop(key, None)
            if b is not None and b.get('known', True):
                g.tell_all(g.pk.buff_remove(tgt.net, b['slot'], DEBUFF))
            amount = by_level(hero.level, (15.0, 40.0, 80.0, 150.0)) + 0.6 * hero.ap
            g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AkshanPassive'))
            if tgt.is_hero and g.t >= self.shield_ready:
                self.shield_ready = g.t + by_level(hero.level, (16.0, 12.0, 8.0, 4.0))
                amount = G.level_stat(40.0, 240.0 / 17.0, hero.level) + 0.35 * hero.bonus['ad']
                hero.shield = getattr(hero, 'shield', {})
                hero.shield['mAllShield'] = amount
                hero.set('mAllShield', amount) if hasattr(hero, 'set') else None
                g.spells.buff(hero, hero, inf, 2, 2.0, key=('kit', 'akshan_shield'), name_hash=SHIELD,
                              undo=lambda: (hero.shield.pop('mAllShield', None), hero.set('mAllShield', 0.0)))
            return
        self.stacks[tgt.net] = (n, g.t + 4.5)
        b = getattr(tgt, 'buff_list', {}).get(key)
        if b is None or n == 1:
            g.spells.buff(hero, tgt, inf, 3, 4.5, key=key, name_hash=DEBUFF)
        else:
            b['until'] = g.t + 4.5
            g.spells.buffs.append([b['until'], tgt, key])
            if b.get('known', True):
                g.q += g.pk.buff_count(tgt.net, b['slot'], hero.net, 4.5, n)

    def attack_start(self, hero, tgt):
        g = self.g
        if getattr(self, 'firing_second', False):
            return
        self.end_camo()
        t0 = g.t
        order = hero.order

        def second(t):
            if not hero.alive:
                return
            target = g.units.get(hero.target) if hero.target else tgt
            if hero.path and hero.order != order:
                # a move order before the shot left: cancelled - the speed instead
                ms = by_level(hero.level, (20.0, 20.0, 20.0, 20.0)) if False else 20.0 + 55.0 * (min(18, hero.level) - 1) / 17.0
                self.decaying_speed(ms * (1.0 + hero.as_bonus), 1.0, flat=True)
                return
            if target is None or not target.alive or dist(hero.pos, target.pos) > hero.range + 200.0 + target.radius:
                return
            g.q += g.pk.spell_in_slot(hero.net, 0x32, 'AkshanPassiveAttack')
            hero.attack_ready = max(hero.attack_ready, t + hero.attack_time())
            crit = hero.crit > 0 and g.rng.random() < hero.crit

            def land(t2, target=target, crit=crit):
                if not (hero.alive and target.alive):
                    return
                amount = (1.0 if target.kind == 'minion' else 0.5) * hero.ad * (1.75 if crit else 1.0)
                dealt = g.deal(hero, target, amount, P.PHYSICAL, basic=True, crit=crit, spell_hash=P.elf('AkshanPassiveAttack'))
                self.stack(target)
            g.at(t + SECOND_FLIGHT, land)
        g.at(t0 + SECOND_AFTER, second)

    def after_attack(self, hero, tgt, dealt):
        self.stack(tgt)

    def decaying_speed(self, amount, seconds, flat=False):
        g, hero = self.g, self.hero
        t0 = g.t
        key = ('kit', 'akshan_ms_' + ('flat' if flat else 'pct'))

        def step(t):
            left = 1.0 - (t - t0) / seconds
            if left <= 0 or not hero.alive:
                hero.remove_mods(key)
            else:
                hero.add_mods(key, {'ms' if flat else 'ms_pct': amount * left})
                g.at(t + 0.25, step)
            g.spells.respeed(hero)
        step(t0)

    # ------------------------------------------------------------------ spells
    def cast_begin(self, c):
        name = c['inf'].name
        if name != 'AkshanW':
            self.end_camo()
        if name == 'AkshanR':
            self.r = {'tgt': c['tgt'], 't0': self.g.t, 'fired': False}
        elif name == 'AkshanW':
            self.camo = {'until': None}

    def resolve(self, c):
        name = c['inf'].name
        if name == 'AkshanR':
            return True                                  # the lock-on: bullets stored until the recast
        if name in ('AkshanRCancel',) or (name == 'AkshanR' and self.r and self.g.t - self.r['t0'] > 0.4):
            self.r_fire()
            return True
        if name == 'AkshanW':
            return True
        return False

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name in ('AkshanR', 'AkshanRCancel'):
            return True                                  # the lock-on's missile: no damage (the bullets are r_fire's)
        if name == 'AkshanQ':
            amount = self.dv('AkshanQ', 'BaseDamage') + 0.7 * hero.bonus['ad']
            if not tgt.is_hero:
                amount *= self.dv('AkshanQ', 'SecondaryTargetDamage') or 0.4
            m = c.get('missile')
            back = m is not None and getattr(m, 'returning', False)
            g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT,
                   spell_hash=P.elf('AkshanQMissileReturn' if back else 'AkshanQMissile'))
            self.stack(tgt)
            if tgt.is_hero:
                self.decaying_speed(0.2 + 0.0005 * hero.ap, 1.0)
            return True
        return False

    # ------------------------------------------------------------------ Comeuppance
    def r_bullets(self):
        rank = self.hero.spell_levels[3]
        interval = (0.625, 0.5208, 0.4167)[min(max(rank, 1), 3) - 1]
        top = (5, 6, 7)[min(max(rank, 1), 3) - 1]
        el = self.g.t - self.r['t0']
        if el >= 2.5 - 1e-3:
            return top
        return min(top, 1 + int(el / interval + 1e-6))

    def r_fire(self):
        g, hero = self.g, self.hero
        if self.r is None or self.r['fired']:
            return
        self.r['fired'] = True
        tgt = self.r['tgt']
        n = self.r_bullets()
        rank = hero.spell_levels[3]
        for i in range(n):
            def shot(t, tgt=tgt):
                if not (hero.alive and tgt is not None and tgt.alive):
                    return
                fly = dist(hero.pos, tgt.pos) / 3200.0

                def land(t2):
                    if not tgt.alive:
                        return
                    if tgt.kind == 'minion':
                        g.deal(hero, tgt, tgt.hp + 1.0, P.TRUE, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AkshanRMissile'))
                        return
                    base = self.dv('AkshanR', 'BonusDamage') + 0.15 * hero.ad
                    missing = 1.0 - tgt.hp / max(1.0, tgt.max_hp)
                    amount = base * (1.0 + 0.3 * hero.crit) * (1.0 + 2.0 * min(1.0, missing / 0.667))
                    g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AkshanRMissile'))
                    self.stack(tgt)
                g.at(t + fly, land)
            g.at(g.t + 0.15 * i, shot)
        self.r = None

    # ------------------------------------------------------------------ Going Rogue
    def end_camo(self):
        if self.camo is not None:
            self.camo = None
            self.hero.stealth_until = 0.0

    def near_cover(self, pos):
        g = self.g
        nav = g.nav
        for k in range(8):
            a = k * math.pi / 4.0
            if nav.is_blocked(pos[0] + 175.0 * math.cos(a), pos[1] + 175.0 * math.sin(a)):
                return True
        labels = getattr(g, 'brush_labels', None)
        if labels is not None:
            try:
                cx, cz = nav.cell(*pos)
                return labels[cz * nav.nx + cx] != 0
            except Exception:
                return False
        return False

    def takedown(self, hero, victim):
        g = self.g
        s = self.scoundrels.pop(victim.net, None)
        if s is None or g.t > s['until'] or g.t - victim.last_hit_by.get(hero.net, -99.0) > 3.0:
            return
        hero.add_gold(100.0, victim.net)
        self.scoundrels.clear()                      # [wiki] claiming one removes the others' marks
        for ally in s['slain']:
            if not ally.alive:
                g.at(g.t + 1.0, lambda t, a=ally: (not a.alive) and a.respawn(t))

    def any_death(self, hero, victim, killer):
        """an ally slain by an enemy champion: that one becomes a Scoundrel for 60 s"""
        g = self.g
        if victim is hero or victim.team != hero.team or killer is None or not killer.is_hero or killer.team == hero.team:
            return
        s = self.scoundrels.setdefault(killer.net, {'until': 0.0, 'slain': []})
        s['until'] = g.t + 60.0
        s['slain'].append(victim)
        from ..spells import info
        g.spells.buff(hero, killer, info(hero.champ, 'AkshanW'), 3, 60.0, key=('kit', 'akshan_hunt'), name_hash=HUNT)

    def tick(self, hero, t):
        g = self.g
        if self.camo is not None and hero.alive:
            if self.near_cover(hero.pos):
                self.camo['until'] = None
            elif self.camo['until'] is None:
                self.camo['until'] = t + 2.0
            if self.camo['until'] is not None and t >= self.camo['until']:
                self.end_camo()
            else:
                hero.stealth_until = t + 0.1
        if self.r is not None and not self.r['fired']:
            tgt = self.r['tgt']
            if tgt is None or not tgt.alive or not hero.alive:
                self.r = None
                hero.cooldowns[3] = max(hero.cooldowns[3], t + 5.0)        # [wiki] cancelled: 5 s
            elif t - self.r['t0'] >= 2.5:
                self.r_fire()


KIT = Akshan
