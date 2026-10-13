"""Aphelios, the Weapon of the Faithful - the live wiki checked against the replays (the packets of his weapons).

Weapons [wiki; m: replays]: Calibrum / Severum / Gravitum / Infernum / Crescendum. The main weapon holds the buff
  Aphelios<Weapon>Manager (type 1), the off-hand ApheliosOffHandBuff<Weapon> (type 1); each buff's 430 counter is that
  weapon's Moonlight (50 at first). A change sends: 262 + 435 of the main's buff, 78 slot 0x2e Aphelios<Weapon>Attack,
  78 slot 0 Aphelios<Weapon>Q, its 430, then the same for the off-hand. Attacks are attack-spells in slot 0x2e named
  Aphelios<Weapon>Attack and spend 1 Moonlight; a Q spends 10 (all that is left under 10). An empty main weapon goes to
  the end of the queue and the next one is assembled over 1 s (ApheliosPReload) with its Q on a 1.5 s cooldown.
Phase (W): swaps main and off-hand (0.8 s static cooldown). Weapon Master: the skill points go to + 4 AD / + 9 % attack
  speed / + 4.5 lethality per rank (Q / W / E keys, 6 ranks; ApheliosPBuffAD / AS / AP counters); Q from level 2, R by
  itself at 6 / 11 / 16.
Basic attacks by weapon [wiki]: Calibrum + 100 range (main); a marked enemy (ApheliosCalibrumBonusRangeDebuff, 4.5 s) is
  hit by 15 + 15 % bonus AD a mark. Severum heals 2 - 8 % (by level) of its damage (5 - 20 % from abilities), the
  excess a shield up to 10 - 160 + 6 % max health. Gravitum slows 30 % falling to 15 % after 0.7 s, 2.5 s
  (ApheliosGravitumDebuff). Infernum: 110 % AD to the target and 75 % (100 % from level 11 [a]) of it to enemies in a
  cone behind it (23 / 30 % to minions). Crescendum: + 0 - 146 % AD by Chakrams (20 at most, 5 s) [a: linear].
Q by main weapon (10 Moonlight + 60 mana, cooldowns by weapon and level):
  Moonshot (Calibrum, 10 - 8 s): a 1450 bolt, first enemy: 80 - 170 + 42 - 60 % bonus AD + 100 % AP physical, marked.
  Onslaught (Severum, 10 - 8 s): 1.75 s, + 25 % (+ 10 % per 100 AP) speed, 6 (+ 2 per 100 % bonus AS) shots at the
    nearest visible enemy (champions first) within 550, Severum and the off-hand by turns, 20 - 41 % AD each.
  Binding Eclipse (Gravitum, 12 - 10 s): every enemy with the Gravitum debuff: 50 - 140 + 32 - 50 % bonus AD + 70 % AP
    magic, rooted 1 s (ApheliosGravitumRoot).
  Duskwave (Infernum, 8 - 5 s): a 650 / 40 degree cone: 20 - 110 + 15 - 21 % bonus AD + 70 % AP; 0.25 s later an off-hand
    shot at each (100 % AD with its effect).
  Sentry (Crescendum, 9 - 6 s): a turret 475 away firing the off-hand at the nearest enemy within 500 for 4 s: 35 - 125
    + 34 - 52 % bonus AD + 50 % AP per shot at his attack speed.
Moonlight Vigil (R): a 1300 light at 1000 stopping at the first enemy champion; champions within 300 take 125 / 175 /
  225 + 20 % bonus AD + 100 % AP; 0.3 s later a main-weapon shot at each (100 % AD) with: Calibrum an empowered mark (50
  / 80 / 110), Severum a 250 / 350 / 450 heal, Gravitum a 99 % slow (root 1.35 with Binding Eclipse), Infernum 50 / 100
  / 150 + 25 % bonus AD more, Crescendum 5 Chakrams.
"""
import math

from . import Kit
from .. import packets as P
from ..units import dist

WEAPONS = ('Calibrum', 'Severum', 'Gravitum', 'Infernum', 'Crescendum')
Q_CD = {'Calibrum': (10.0, 8.0), 'Severum': (10.0, 8.0), 'Gravitum': (12.0, 10.0), 'Infernum': (8.0, 5.0), 'Crescendum': (9.0, 6.0)}
MARK, MARK_SELF = P.elf('ApheliosCalibrumBonusRangeDebuff'), P.elf('ApheliosCalibrumBonusRangeBuff')
GRAV, ROOT = P.elf('ApheliosGravitumDebuff'), P.elf('ApheliosGravitumRoot')
RELOAD = P.elf('ApheliosPReload')
POINT_BUFFS = (P.elf('ApheliosPBuffAD'), P.elf('ApheliosPBuffAS'), P.elf('ApheliosPBuffAP'))


def lerp(a, b, level):
    return a + (b - a) * (max(1, min(18, level)) - 1) / 17.0


class Aphelios(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.queue = list(WEAPONS)
        self.ammo = {w: 50 for w in WEAPONS}
        self.q_ready = {w: 0.0 for w in WEAPONS}
        self.points = [0, 0, 0]
        self.started = False
        self.assembling_until = 0.0
        self.chakrams, self.chakram_until = 0, 0.0
        self.onslaught = None

    @property
    def main(self):
        return self.queue[0]

    @property
    def off(self):
        return self.queue[1]

    def inf(self):
        from ..spells import info
        return info(self.hero.champ, 'ApheliosW')

    def bad(self):
        return self.hero.bonus['ad']

    # ------------------------------------------------------------------ the weapons' packets
    def show(self, which, w, add=True):
        g, hero = self.g, self.hero
        key = ('kit', 'aph_' + which)
        old = getattr(hero, 'buff_list', {}).pop(key, None)
        if old is not None and old.get('known', True):
            g.tell_all(g.pk.buff_remove(hero.net, old['slot'], old['hash']))
        if not add:
            return
        h = P.elf(f'Aphelios{w}Manager' if which == 'main' else f'ApheliosOffHandBuff{w}')
        g.spells.buff(hero, hero, self.inf(), 1, 25000.0, key=key, name_hash=h)
        if which == 'main':
            g.q += g.pk.spell_in_slot(hero.net, 0x2e, f'Aphelios{w}Attack')
            g.q += g.pk.spell_in_slot(hero.net, 0, f'Aphelios{w}Q')
            hero.slot_names[0] = f'Aphelios{w}Q'
        self.count(which)

    def count(self, which):
        g, hero = self.g, self.hero
        b = getattr(hero, 'buff_list', {}).get(('kit', 'aph_' + which))
        w = self.main if which == 'main' else self.off
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], b['hash'], self.ammo[w])

    def set_main_stats(self):
        hero = self.hero
        hero.remove_mods(('kit', 'aph_calibrum'))
        if self.main == 'Calibrum':
            hero.add_mods(('kit', 'aph_calibrum'), {'range': 100.0})
        hero.cooldowns[0] = max(self.g.t, self.q_ready[self.main])
        hero.refresh_bits()

    def spend(self, n):
        g = self.g
        w = self.main
        self.ammo[w] = max(0, self.ammo[w] - n)
        self.count('main')
        if self.ammo[w] <= 0:
            # empty: to the end of the queue; the next one assembled over 1 s, its Q waiting 1.5 s
            self.queue.append(self.queue.pop(0))
            nxt = self.queue.pop(2) if len(self.queue) > 2 else self.queue[1]
            self.queue.insert(0, nxt)
            self.ammo[self.main] = 50
            self.assembling_until = g.t + 1.0
            self.q_ready[self.main] = g.t + 1.5
            g.spells.buff(self.hero, self.hero, self.inf(), 2, 1.0, key=('kit', 'aph_reload'), name_hash=RELOAD)
            g.at(g.t + 1.0, lambda t: self.hero.alive and (self.show('main', self.main), self.set_main_stats()))

    # ------------------------------------------------------------------ points and levels
    def skill_points(self, hero):
        return hero.level - sum(self.points)

    def level_spell(self, hero, slot):
        g = self.g
        if slot == 3 or self.skill_points(hero) <= 0 or self.points[slot] >= 6:
            return False
        self.points[slot] += 1
        n = self.points[slot]
        key = ('kit', 'aph_point', slot)
        b = getattr(hero, 'buff_list', {}).get(key)
        if b is None:
            g.spells.buff(hero, hero, self.inf(), 27, 25000.0, key=key, name_hash=POINT_BUFFS[slot])
            b = hero.buff_list.get(key)
        if b is not None and b.get('known', True):
            g.q += g.pk.buff_counter(hero.net, b['slot'], POINT_BUFFS[slot], n)
        hero.remove_mods(('kit', 'aph_points'))
        hero.add_mods(('kit', 'aph_points'), {'ad': 4.0 * self.points[0], 'as': 0.09 * self.points[1],
                                              'lethality': 4.5 * self.points[2]})
        return True

    def learnt(self, hero, slot):
        return (slot == 0 and hero.level >= 2) or slot == 1 or (slot == 3 and hero.level >= 6)

    # ------------------------------------------------------------------ attacks
    def attack_override(self, hero, tgt):
        if self.g.t < self.assembling_until:
            return None
        return {'slot': 0x2e, 'name': f'Aphelios{self.main}Attack', 'package': 0, 'champion': hero.name}

    def attack_hit(self, hero, tgt, amount):
        w = self.main
        if w == 'Infernum':
            amount *= 1.1
        elif w == 'Crescendum' and self.g.t < self.chakram_until:
            amount += 1.46 * hero.ad * min(20, self.chakrams) / 20.0
        return amount

    def after_attack(self, hero, tgt, dealt):
        self.weapon_hit(self.main, tgt, dealt, ability=False)
        self.spend(1)

    def weapon_hit(self, w, tgt, dealt, ability):
        g, hero = self.g, self.hero
        if not tgt.alive and w != 'Severum':
            return
        if w == 'Severum':
            pct = lerp(0.05, 0.2, hero.level) if ability else lerp(0.02, 0.08, hero.level)
            over = hero.hp + dealt * pct - hero.max_hp
            hero.heal(dealt * pct)
            if over > 0:
                hero.shield = getattr(hero, 'shield', {})
                cap = lerp(10.0, 160.0, hero.level) + 0.06 * hero.max_hp
                hero.shield['mAllShield'] = min(cap, hero.shield.get('mAllShield', 0.0) + over)
        elif w == 'Gravitum':
            g.spells.slow(hero, tgt, self.inf(), 0.3, 2.5, name_hash=GRAV)
            tgt.aph_gravitum = g.t + 2.5
            g.at(g.t + 0.7, lambda t: tgt.alive and self.inf().name in getattr(tgt, 'slows', {}) and
                 (tgt.slows.__setitem__(self.inf().name, 0.15), g.spells.respeed(tgt)))
        elif w == 'Infernum' and not ability:
            share = (1.0 if hero.level >= 11 else 0.75)
            d = dist(hero.pos, tgt.pos) or 1.0
            ux, uz = (tgt.pos[0] - hero.pos[0]) / d, (tgt.pos[1] - hero.pos[1]) / d
            for o in g.spells.enemies(hero):
                if o is tgt:
                    continue
                rel = (o.pos[0] - tgt.pos[0], o.pos[1] - tgt.pos[1])
                f = rel[0] * ux + rel[1] * uz
                s = abs(-rel[0] * uz + rel[1] * ux)
                if 0 < f <= 350.0 + o.radius and s <= f * 0.42 + o.radius:
                    g.deal(hero, o, dealt * share * ((0.3 if hero.level >= 11 else 0.23) if o.kind == 'minion' else 1.0),
                           P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('ApheliosInfernumSplashMis'))
        elif w == 'Calibrum':
            marks = getattr(tgt, 'aph_marks', 0)
            if marks and g.t < getattr(tgt, 'aph_mark_until', 0.0):
                tgt.aph_marks = 0
                g.deal(hero, tgt, (15.0 + 0.15 * self.bad()) * marks, P.PHYSICAL, basic=False, source=P.SRC_DIRECT,
                       spell_hash=P.elf('ApheliosCalibrumAttack'))

    def shot(self, w, tgt, amount, ability=True, name=None):
        """an automatic weapon shot (Onslaught, Duskwave, the Vigil, the Sentry)"""
        g, hero = self.g, self.hero
        if not (hero.alive and tgt.alive):
            return
        dealt = g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT,
                       spell_hash=P.elf(name or f'Aphelios{w}Attack'))
        self.weapon_hit(w, tgt, dealt, ability)

    # ------------------------------------------------------------------ the templates' copies of the weapon packets
    def skip_template(self, e):
        v = e.get('values') if isinstance(e.get('values'), dict) else {}
        if e['pid'] == 78 and isinstance(v.get('+0x10'), dict) and v['+0x10'].get('+0xf') in ('00', '2e'):
            return True
        if e['pid'] in (435, 262, 430, 282):
            mine = {P.u32(P.elf(f'Aphelios{w}Manager')) for w in WEAPONS} |                    {P.u32(P.elf(f'ApheliosOffHandBuff{w}')) for w in WEAPONS}
            if v.get('+0x64') in mine or v.get('+0x18') in mine or v.get('+0x14') in mine:
                return True
        return False

    # ------------------------------------------------------------------ casts
    def cast_request(self, hero, slot, aim, target):
        g = self.g
        if slot == 1:
            if g.t < self.assembling_until or g.t < hero.cooldowns[1]:
                return 'Aphelios: Phase not ready'
        if slot == 0 and g.t < self.assembling_until:
            return 'Aphelios: assembling'
        return None

    def cast_begin(self, c):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'ApheliosW':
            self.queue[0], self.queue[1] = self.queue[1], self.queue[0]
            self.show('main', self.main)
            self.show('off', self.off)
            self.set_main_stats()
            g.at(g.t + 0.001, lambda t: (hero.cooldowns.__setitem__(1, t + 0.8), hero.refresh_bits()))
        elif name.startswith('Aphelios') and name.endswith('Q'):
            w = self.main
            lo, hi = Q_CD[w]
            cd = lerp(lo, hi, hero.level) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
            self.q_ready[w] = g.t + cd
            g.at(g.t + 0.001, lambda t: (hero.cooldowns.__setitem__(0, self.q_ready[w]), hero.refresh_bits()))
            c['weapon'] = w
            self.spend(10 if self.ammo[w] >= 10 else self.ammo[w])

    def resolve(self, c):
        name = c['inf'].name
        w = c.get('weapon')
        if w == 'Severum':
            self.onslaught_start()
            return True
        if w == 'Gravitum':
            self.eclipse()
            return True
        if w == 'Infernum':
            self.duskwave(c)
            return True
        if w == 'Crescendum':
            self.sentry(c)
            return True
        if name == 'ApheliosR':
            self.vigil(c)
            return True
        return name == 'ApheliosW'

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        if c.get('weapon') == 'Calibrum':
            amount = lerp(80.0, 170.0, hero.level) + lerp(0.42, 0.6, hero.level) * self.bad() + hero.ap
            g.deal(hero, tgt, amount, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('ApheliosCalibrumQ'))
            if tgt.alive:
                self.mark(tgt)
            return True
        if c['inf'].name in ('ApheliosR',) or c.get('weapon'):
            return True                                  # the weapons' effects are the kit's (resolve)
        return False

    def mark(self, tgt, empowered=0.0):
        g, hero = self.g, self.hero
        tgt.aph_marks = getattr(tgt, 'aph_marks', 0) + 1 if g.t < getattr(tgt, 'aph_mark_until', 0.0) else 1
        tgt.aph_mark_until = g.t + 4.5
        g.spells.buff(hero, tgt, self.inf(), 3, 4.5, key=('kit', 'aph_mark'), name_hash=MARK)
        g.spells.buff(hero, hero, self.inf(), 2, 4.5, key=('kit', 'aph_mark_self'), name_hash=MARK_SELF)

    def onslaught_start(self):
        g, hero = self.g, self.hero
        n = 6 + int(2 * max(0.0, hero.as_bonus))
        hero.add_mods(('kit', 'aph_onslaught'), {'ms_pct': 0.25 + 0.001 * hero.ap})
        g.spells.respeed(hero)
        for i in range(n):
            def fire(t, i=i):
                if not hero.alive:
                    return
                foes = [o for o in g.spells.enemies(hero) if dist(o.pos, hero.pos) <= 550.0 and g.seen_by(hero.team, o)]
                if not foes:
                    return
                tgt = min(foes, key=lambda o: (not o.is_hero, dist(o.pos, hero.pos)))
                w = 'Severum' if i % 2 else self.off
                self.shot(w, tgt, lerp(0.2, 0.41, hero.level) * hero.ad)
            g.at(g.t + 1.75 * i / n, fire)
        g.at(g.t + 1.75, lambda t: (hero.remove_mods(('kit', 'aph_onslaught')), g.spells.respeed(hero)))

    def eclipse(self, root_time=1.0):
        g, hero = self.g, self.hero
        for o in g.spells.enemies(hero):
            if getattr(o, 'aph_gravitum', 0.0) > g.t:
                g.deal(hero, o, lerp(50.0, 140.0, hero.level) + lerp(0.32, 0.5, hero.level) * self.bad() + 0.7 * hero.ap,
                       P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('ApheliosGravitumQ'))
                if o.alive:
                    t = root_time if getattr(o, 'aph_gravitum_99', 0.0) < g.t else 1.35
                    g.spells.cc(hero, o, self.inf(), 12, t, root=True, name_hash=ROOT)
                o.aph_gravitum = 0.0

    def duskwave(self, c):
        g, hero = self.g, self.hero
        d = c['direction']
        off = self.off
        hit = []
        for o in g.spells.enemies(hero):
            rel = (o.pos[0] - hero.pos[0], o.pos[1] - hero.pos[1])
            r = math.hypot(*rel)
            if r > 650.0 + o.radius or r == 0:
                continue
            if math.degrees(math.acos(max(-1.0, min(1.0, (rel[0] * d[0] + rel[1] * d[1]) / r)))) <= 20.0:
                g.deal(hero, o, lerp(20.0, 110.0, hero.level) + lerp(0.15, 0.21, hero.level) * self.bad() + 0.7 * hero.ap,
                       P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('ApheliosInfernumQ'))
                hit.append(o)
        g.at(g.t + 0.25, lambda t: [self.shot(off, o, hero.ad) for o in hit])

    def sentry(self, c):
        g, hero = self.g, self.hero
        d = c['direction']
        place = (hero.pos[0] + d[0] * 475.0, hero.pos[1] + d[1] * 475.0)
        off = self.off
        state = {'active_until': None, 'until': g.t + 20.0}

        def step(t):
            if t >= state['until'] or not hero.alive:
                return
            foes = [o for o in g.spells.enemies(hero) if dist(o.pos, place) <= 500.0 and g.seen_by(hero.team, o)]
            if foes:
                if state['active_until'] is None:
                    state['active_until'] = t + 4.0
                    state['until'] = min(state['until'], t + 4.0)
                tgt = min(foes, key=lambda o: dist(o.pos, place))
                self.shot(off, tgt, lerp(35.0, 125.0, hero.level) + lerp(0.34, 0.52, hero.level) * self.bad() + 0.5 * hero.ap,
                          name='ApheliosCrescendumTurretMis')
                g.at(t + 1.0 / max(0.2, hero.attack_speed), step)
            else:
                g.at(t + 0.1, step)
        g.at(g.t + 0.35, step)

    def vigil(self, c):
        g, hero = self.g, self.hero
        d = c['direction']
        rank = max(1, hero.spell_levels[3])
        w = self.main
        best = None
        for o in g.heroes:
            if not o.alive or o.team == hero.team:
                continue
            rel = (o.pos[0] - hero.pos[0], o.pos[1] - hero.pos[1])
            f = rel[0] * d[0] + rel[1] * d[1]
            if 0 < f <= 1300.0 and abs(-rel[0] * d[1] + rel[1] * d[0]) <= 120.0 + o.radius and (best is None or f < best[0]):
                best = (f, o)
        if best is None:
            return
        center = best[1].pos
        delay = best[0] / 1000.0

        def blast(t):
            hits = [o for o in g.heroes if o.alive and o.team != hero.team and dist(o.pos, center) <= 300.0 + o.radius]
            for o in hits:
                g.deal(hero, o, (75.0 + 50.0 * rank) + 0.2 * self.bad() + hero.ap, P.PHYSICAL, basic=False,
                       source=P.SRC_DIRECT, spell_hash=P.elf('ApheliosR'))
            if w == 'Severum' and hits:
                hero.heal(150.0 + 100.0 * rank)

            def follow(t2):
                for o in hits:
                    extra = (50.0 * rank + 0.25 * self.bad()) if w == 'Infernum' else 0.0
                    self.shot(w, o, hero.ad + extra)
                    if w == 'Calibrum':
                        self.mark(o)
                    elif w == 'Gravitum' and o.alive:
                        g.spells.slow(hero, o, self.inf(), 0.99, 2.5, name_hash=GRAV)
                        o.aph_gravitum = o.aph_gravitum_99 = g.t + 2.5
                if w == 'Crescendum':
                    self.chakrams, self.chakram_until = min(20, self.chakrams + 5 + len(hits)), g.t + 5.0
            g.at(t + 0.3, follow)
        g.at(g.t + delay, blast)

    # ------------------------------------------------------------------ the frame
    def tick(self, hero, t):
        g = self.g
        if not self.started:
            self.started = True
            self.show('main', self.main)
            self.show('off', self.off)
            self.set_main_stats()
        want = sum(1 for x in (6, 11, 16) if hero.level >= x)
        if hero.spell_levels[3] < want:
            hero.spell_levels[3] = want
            g.q += g.pk.skill_level(hero.net, 3, want, self.skill_points(hero))
            hero.refresh_bits()
        if self.chakrams and t >= self.chakram_until:
            self.chakrams = 0


KIT = Aphelios
