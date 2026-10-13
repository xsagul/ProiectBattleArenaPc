"""Akali, the Rogue Assassin - the live wiki (V26.17, = the 16.20 data) checked against the replays.

Assassin's Mark (P) [wiki, data AkaliP]: her ability damage to an enemy champion makes a ring (radius 500) around it for
  4 s (refreshed by further ability damage to champions; one at a time, none while empowered); for 2 s she gets 30 / 40
  / 50 / 60 % move speed (levels 1 / 6 / 11 / 16) moving away from its center. Leaving it: empowered for 4 s - again the
  speed for 2 s moving toward enemy champions [a: within 1000], doubled attack range, and the next attack (not at a
  structure / ward) deals 35 - 182 (data: + 3 a level, + 9 from 8, + 15 from 14) + 60 % bonus AD + 55 % AP bonus magic
  damage (AkaliP). [m: replays] leaving sends AkaliPWeapon (type 2, 4 s), AkaliPMaterialVFX (type 1, 20 s) and three
  78s into slot 0x2d (AkaliPVFXMis1 / AkaliPVFXMis2 / AkaliPVFXMisEnemy1); her attacks all go through slot 0x31, the
  empowered one as AkaliBasicAttackPassive[Melee][Minion] (melee: the target within her plain range; minion: a minion);
  its hit ends both buffs. The templates' fixed-time copies of these are left out (skip_template).
Five Point Strike (Q): generic (cone, damage, slow) [a: the slow's "beyond a certain range" is not known: on all].
Twilight Shroud (W) [wiki, data AkaliW]: 100 energy over 0.4 s, max energy + 100 while it lasts (5 - 7 s by rank), the
  shroud at 250 ahead growing [m: its smoke missiles, 150 / s for 465] from radius 140 (CloudRadius); inside she is
  invisible unless dashing; an attack or a cast breaks it for 1 s, less from level 7 (1, 0.9 at 7, 0.825 at 10, 0.725 at
  13, 0.625 at 16). The speed is core/statbuffs.py's.
Shuriken Flip (E) [wiki, data AkaliE]: the flip and the shuriken are generic (templates); its hit deals 30 % of
  (BaseDamage + 100 % AD + 110 % AP) and marks (13ec2f08, 3 s). Recast (AkaliEb): a dash at the marked enemy, following
  it, at 1720 [m: template], dealing the other 70 % (AkaliEb) on arrival.
Perfect Execution (R) [wiki, data AkaliR]: dash in the target's direction 750, at least 150 past the first enemy met
  (up to 900) [m: 659 - 836 in the replays], at 1500; enemies passed take 110 / 220 / 330 + 50 % bonus AD + 30 % AP.
  The recast (AkaliRb) after 2.5 s within 10 s: an 800 dash at 3000 [wiki], enemies passed take 70 / 140 / 210 + 30 % AP,
  x 1 - 3 by their missing health (x 3 at 30 % health or less). [a] the full cooldown starts with the recast or when the
  window ends.
"""
import math

from . import Kit
from .. import packets as P
from ..units import dist

WEAPON, MATERIAL = P.elf('AkaliPWeapon'), P.elf('AkaliPMaterialVFX')
MARK = Kit.h('13ec2f08')
PVFX = ('AkaliPVFXMis1', 'AkaliPVFXMis2', 'AkaliPVFXMisEnemy1')
RING, RING_TIME, EMPOWER_TIME = 500.0, 4.0, 4.0


def kama_damage(level):
    v = 35.0
    for lv in range(2, max(1, min(18, level)) + 1):
        v += 3.0 if lv < 8 else 9.0 if lv < 14 else 15.0
    return v


def restealth(level):
    v = 1.0
    for lv, d in ((7, -0.1), (10, -0.075), (13, -0.1), (16, -0.1)):
        if level >= lv:
            v += d
    return v


class Akali(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.ring = None                     # (center, until)
        self.ring_speed_until = 0.0
        self.empowered_until = 0.0
        self.empower_speed_until = 0.0
        self.shroud = None                   # (center, t0, until)
        self.broke_until = 0.0
        self.r = None                        # {'first': t, 'until': t}

    def dv(self, spell, name):
        from ..spells import info
        rank = self.hero.spell_levels['QWER'.index({'AkaliQ': 'Q', 'AkaliW': 'W', 'AkaliE': 'E', 'AkaliR': 'R'}[spell])]
        return info(self.hero.champ, spell).data_value((name,), rank) or 0.0

    def speed_pct(self):
        lv = self.hero.level
        return 0.3 + 0.1 * sum(1 for x in (6, 11, 16) if lv >= x)

    # ------------------------------------------------------------------ the templates' copies of the passive
    def skip_template(self, e):
        v = e.get('values') if isinstance(e.get('values'), dict) else {}
        if e['pid'] == 287 and e.get('field') == 'mAttackRange':
            return True                                  # the empowered range is the kit's
        if e['pid'] == 287 and e.get('field') == 'ActionState':
            b, a = (v.get('ActionState') or [0, 0])[:2]
            if isinstance(a, int) and isinstance(b, int) and (a ^ b) & 0x20:
                return True                              # the shroud's invisibility is the kit's
        if e['pid'] == 435 and v.get('+0x64') in (P.u32(WEAPON), P.u32(MATERIAL)):
            return True
        if e['pid'] == 78:
            txt = (v.get('+0x20') or {}).get('text') if isinstance(v.get('+0x20'), dict) else None
            try:
                name = bytes.fromhex(txt).rstrip(b'\0').decode() if txt else ''
            except Exception:
                name = ''
            return name in PVFX
        return False

    # ------------------------------------------------------------------ Assassin's Mark
    def dealt(self, hero, tgt, dealt, basic, spell_hash, source=None):
        g = self.g
        if basic or not tgt.is_hero or tgt.team == hero.team or spell_hash == P.elf('AkaliP'):
            return
        if g.t < self.empowered_until:
            return
        if self.ring is None or g.t >= self.ring[1]:
            self.ring = (tgt.pos, g.t + RING_TIME)
            self.ring_speed_until = g.t + 2.0
        else:
            self.ring = (self.ring[0], g.t + RING_TIME)

    def empower(self):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'AkaliQ')
        self.ring = None
        self.empowered_until = g.t + EMPOWER_TIME
        self.empower_speed_until = g.t + 2.0
        g.spells.buff(hero, hero, inf, 2, EMPOWER_TIME, key=('kit', 'akali_weapon'), name_hash=WEAPON)
        g.spells.buff(hero, hero, inf, 1, 20.0, key=('kit', 'akali_material'), name_hash=MATERIAL)
        for n in PVFX:
            g.q += g.pk.spell_in_slot(hero.net, 0x2d, n)
        hero.add_mods(('kit', 'akali_range'), {'range': hero.base.get('range', 125.0)})

    def unempower(self):
        g, hero = self.g, self.hero
        self.empowered_until = 0.0
        hero.remove_mods(('kit', 'akali_range'))
        for key, h in ((('kit', 'akali_weapon'), WEAPON), (('kit', 'akali_material'), MATERIAL)):
            b = getattr(hero, 'buff_list', {}).pop(key, None)
            if b is not None and b.get('known', True):
                g.tell_all(g.pk.buff_remove(hero.net, b['slot'], h))

    def attack_override(self, hero, tgt):
        g = self.g
        if g.t >= self.empowered_until or tgt.is_structure or tgt.kind == 'ward':
            return None
        melee = dist(hero.pos, tgt.pos) <= hero.base.get('range', 125.0) + hero.radius + tgt.radius
        name = 'AkaliBasicAttackPassive' + ('Melee' if melee else '') + ('Minion' if tgt.kind == 'minion' else '')
        self.kama = tgt.net
        g.q += g.pk.spell_in_slot(hero.net, 0x31, name)
        return {'slot': 0x31, 'name': name, 'package': 0, 'champion': hero.name}

    def after_attack(self, hero, tgt, dealt):
        g = self.g
        if getattr(self, 'kama', None) == tgt.net and g.t < self.empowered_until:
            self.kama = None
            amount = kama_damage(hero.level) + 0.6 * hero.bonus['ad'] + 0.55 * hero.ap
            self.unempower()
            if tgt.alive:
                g.deal(hero, tgt, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AkaliP'))
        if hero.alive:
            self.broke_until = g.t + restealth(hero.level)

    # ------------------------------------------------------------------ casts
    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        self.broke_until = g.t + restealth(hero.level)
        if name == 'AkaliW':
            d = c['direction']
            center = (hero.pos[0] + d[0] * 250.0, hero.pos[1] + d[1] * 250.0)
            dur = self.dv('AkaliW', 'BaseDuration') or 5.0
            self.shroud = (center, g.t, g.t + dur)
            self.broke_until = 0.0
            hero.add_mods(('kit', 'akali_w_energy'), {'par': 100.0})
            for i in range(4):
                g.at(g.t + 0.1 * (i + 1), lambda t: hero.alive and hero.set_par(hero.par + 25.0))
        elif name == 'AkaliR':
            # [m: template] the dash begins with the cast; the recast after 2.5 s from now
            self.r = {'first': g.t, 'until': g.t + 10.0}
            c['kit_dash'] = True
            self.r_dash(c, first=True)
            g.at(g.t + 0.001, lambda t, t0=g.t: self.r_hold(t0 + 2.5 - t))

    def resolve(self, c):
        name = c['inf'].name
        if name == 'AkaliEb':
            return self.e_dash(c)
        if name == 'AkaliR':
            return True                                  # dashed at the cast's start (cast_begin)
        if name == 'AkaliRb':
            return self.r_dash(c, first=False)
        return False

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'AkaliE':
            total = self.dv('AkaliE', 'BaseDamage') + hero.base_ad + hero.bonus['ad'] + 1.1 * hero.ap
            g.deal(hero, tgt, 0.3 * total, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash('AkaliE'))
            if tgt.alive:
                from ..spells import info
                g.spells.buff(hero, tgt, info(hero.champ, 'AkaliE'), 3, 3.0, key=('kit', 'akali_mark'), name_hash=MARK)
                self.e_mark = (tgt, g.t + 3.0)
            return True
        return False

    # ------------------------------------------------------------------ Shuriken Flip's recast
    def e_dash(self, c):
        g, hero = self.g, self.hero
        tgt, until = getattr(self, 'e_mark', (None, 0.0))
        if tgt is None or not tgt.alive or g.t > until + 0.5:
            return True
        self.e_mark = (None, 0.0)
        speed = 1720.0
        hero.path, hero.order, hero.dashing = None, None, True
        g.q += g.pk.dash(g.t, hero, [hero.pos, tgt.pos], speed)
        total = self.dv('AkaliE', 'BaseDamage') + hero.base_ad + hero.bonus['ad'] + 1.1 * hero.ap

        def step(t):
            if not hero.alive:
                hero.dashing = False
                return
            d = dist(hero.pos, tgt.pos)
            reach = hero.radius + tgt.radius
            stepl = speed / 30.0
            if d - reach <= stepl or not tgt.alive:
                hero.dashing = False
                if tgt.alive:
                    g.deal(hero, tgt, 0.7 * total, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AkaliEb'))
                    hero.target, hero.order = tgt.net, ('attack', tgt.net)      # [wiki] ordered to attack it
                return
            hero.pos = (hero.pos[0] + (tgt.pos[0] - hero.pos[0]) / d * stepl, hero.pos[1] + (tgt.pos[1] - hero.pos[1]) / d * stepl)
            g.at(t + 1.0 / 30.0, step)
        step(g.t)
        return True

    # ------------------------------------------------------------------ Perfect Execution
    def r_dash(self, c, first):
        g, hero = self.g, self.hero
        rank = c['rank']
        if first:
            tgt = c['tgt']
            aim = tgt.pos if tgt is not None else c['aim']
            dx, dz = aim[0] - hero.pos[0], aim[1] - hero.pos[1]
            dd = math.hypot(dx, dz) or 1.0
            d = (dx / dd, dz / dd)
            length = min(900.0, max(750.0, dd + 150.0)) if tgt is not None and dd <= 750.0 else 750.0
            speed = 1500.0
            amount = lambda o: self.dv('AkaliR', 'BaseDamage') + 0.5 * hero.bonus['ad'] + 0.3 * hero.ap
            hname = P.elf('AkaliR')
        else:
            d = c['direction']
            length, speed = 800.0, 3000.0

            def amount(o):
                base = self.dv('AkaliR', 'R2BaseDamage') + 0.3 * hero.ap
                missing = 1.0 - o.hp / max(1.0, o.max_hp)
                return base * (1.0 + 2.0 * min(1.0, missing / 0.7))
            hname = P.damage_hash('AkaliRb')
            self.r = None
            g.at(g.t + 0.001, lambda t: self.r_full())
        start = hero.pos
        dest = (start[0] + d[0] * length, start[1] + d[1] * length)
        dest = g.nav.nearest_free(*dest) or dest
        hero.path, hero.order, hero.dashing = None, None, True
        g.q += g.pk.dash(g.t, hero, [start, dest], speed)
        hit = set()

        def step(t):
            if not hero.alive:
                hero.dashing = False
                return
            left = dist(hero.pos, dest)
            stepl = speed / 30.0
            nxt = dest if left <= stepl else (hero.pos[0] + (dest[0] - hero.pos[0]) / left * stepl,
                                              hero.pos[1] + (dest[1] - hero.pos[1]) / left * stepl)
            from ..spells import _point_segment
            for o in g.spells.enemies(hero):
                if o.net not in hit and _point_segment(o.pos, hero.pos, nxt)[0] <= 110.0 + o.radius:
                    hit.add(o.net)
                    g.deal(hero, o, amount(o), P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=hname)
            hero.pos = nxt
            if left <= stepl:
                hero.dashing = False
                return
            g.at(t + 1.0 / 30.0, step)
        step(g.t)
        return True

    def r_hold(self, seconds):
        hero = self.hero
        hero.cooldowns[3] = self.g.t + seconds
        hero.refresh_bits()

    def r_full(self):
        from ..spells import info
        hero = self.hero
        cd = info(hero.champ, 'AkaliR').cooldown(hero.spell_levels[3]) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        hero.cooldowns[3] = self.g.t + cd
        hero.refresh_bits()

    # ------------------------------------------------------------------ the frame
    def tick(self, hero, t):
        g = self.g
        if self.ring is not None:
            center, until = self.ring
            if t >= until:
                self.ring = None
            elif dist(hero.pos, center) > RING:
                self.empower()
        if self.empowered_until and t >= self.empowered_until:
            self.unempower()
        # move speed: away from the ring's center / toward enemy champions while empowered
        fast = False
        if hero.path:
            nxt = hero.path[0]
            v = (nxt[0] - hero.pos[0], nxt[1] - hero.pos[1])
            if self.ring is not None and t < self.ring_speed_until:
                c = self.ring[0]
                fast = v[0] * (hero.pos[0] - c[0]) + v[1] * (hero.pos[1] - c[1]) > 0
            elif t < self.empower_speed_until:
                foes = [o for o in g.heroes if o.alive and o.team != hero.team and dist(o.pos, hero.pos) <= 1000.0]
                fast = any(v[0] * (o.pos[0] - hero.pos[0]) + v[1] * (o.pos[1] - hero.pos[1]) > 0 for o in foes)
        has = ('kit', 'akali_p_ms') in hero.mods
        if fast and not has:
            hero.add_mods(('kit', 'akali_p_ms'), {'ms_pct': self.speed_pct()})
            g.spells.respeed(hero)
        elif not fast and has:
            hero.remove_mods(('kit', 'akali_p_ms'))
            g.spells.respeed(hero)
        # Twilight Shroud: invisible inside it, unless dashing or just after an attack / cast
        if self.shroud is not None:
            center, t0, until = self.shroud
            if t >= until:
                self.shroud = None
                hero.remove_mods(('kit', 'akali_w_energy'))
                hero.set_par(min(hero.par, hero.max_par))
            else:
                radius = min(140.0 + 465.0, 140.0 + 150.0 * (t - t0))
                if dist(hero.pos, center) <= radius and not getattr(hero, 'dashing', False) and t >= self.broke_until:
                    hero.stealth_until = t + 0.1
        if self.r is not None and t >= self.r['until']:
            self.r = None
            self.r_full()

    def died(self, hero):
        self.ring = None
        self.unempower()
        self.shroud = None


KIT = Akali
