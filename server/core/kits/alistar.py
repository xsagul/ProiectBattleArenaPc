"""Alistar, the Minotaur - the live wiki checked against the 16.20 data and the replays.

Triumphant Roar (P) [wiki]: a stack per enemy champion he stuns or displaces with an ability and per enemy minion /
  non-epic monster dying within 1000; 7 when an enemy champion or epic monster dies within 950. At 7 (and its 3 s static
  cooldown over) he consumes them: heals himself 5 % of his maximum health and allied champions within 1000 7 % of it;
  [m: replays] the roar puts AlistarPassiveHeal in slot 0x2e and AlistarPassiveHealMis in slot 0x2f (78). Stacks are lost
  on death. (The state buff 59074e08 is the templates'.)
Pulverize (Q) [wiki, data]: hits 0.167 s after the cast [m: template]: enemies within 375 take 60 - 220 + 80 % AP magic
  and are knocked up and stunned 1 s (Pulverize, type 30).
Headbutt (W) [wiki, data]: the dash is the templates'; on arrival the target, if within 400, takes 55 - 275 + 100 % AP
  magic, is knocked back 700 over 0.5 s from where Alistar started (9417d200, type 31) and stunned 0.75 s (TH8>-named
  bc5c...: the template's stun hash) [m].
Trample (E) [wiki, data]: the ticks are generic (0.535 s script timer, 8 - 20 + 7 % AP); a tick that damages a champion
  adds a stack (5 at most); at 5 the next attack at a champion within 5 s (data FullChargeDuration) deals 20 + 15 a level
  magic and stuns 1 s, and ends Trample.
Unbreakable Will (R) [wiki, data]: cleanses his crowd control; incoming damage (not true) - 55 / 65 / 75 % for 7 s.
"""
from . import Kit
from .. import packets as P
from ..units import dist

KNOCKUP_Q = P.elf('Pulverize')
KNOCK_W, STUN_W = Kit.h('9417d200'), None
CC_TYPES = (5, 7, 8, 11, 12, 22, 23, 24, 25, 29, 30, 31, 32, 35)


class Alistar(Kit):
    def __init__(self, game, hero):
        super().__init__(game, hero)
        self.stacks = 0
        self.roar_ready = 0.0
        self.e = None                        # {'stacks', 'until', 'counted': set of tick times, 'charged_until'}

    def dv(self, spell, name):
        from ..spells import info
        k = {'Pulverize': 0, 'Headbutt': 1, 'AlistarE': 2, 'FerociousHowl': 3}[spell]
        return info(self.hero.champ, spell).data_value((name,), self.hero.spell_levels[k]) or 0.0

    # ------------------------------------------------------------------ Triumphant Roar
    def gain(self, n):
        g, hero = self.g, self.hero
        if not hero.alive:
            return
        self.stacks = min(7, self.stacks + n)
        self.try_roar()

    def try_roar(self):
        g, hero = self.g, self.hero
        if self.stacks < 7 or g.t < self.roar_ready or not hero.alive:
            return
        self.stacks = 0
        self.roar_ready = g.t + 3.0
        g.q += g.pk.spell_in_slot(hero.net, 0x2e, 'AlistarPassiveHeal')
        g.q += g.pk.spell_in_slot(hero.net, 0x2f, 'AlistarPassiveHealMis')
        hero.heal(0.05 * hero.max_hp)
        for a in g.heroes:
            if a is not hero and a.alive and a.team == hero.team and dist(a.pos, hero.pos) <= 1000.0:
                a.heal(0.07 * hero.max_hp)

    def any_unit_death(self, hero, u, killer):
        if u.team == hero.team or not hero.alive or dist(u.pos, hero.pos) > 1000.0:
            return
        epic = u.kind == 'monster' and any(k in u.name for k in ('Baron', 'Dragon', 'dragon', 'Herald', 'Horde', 'Atakhan'))
        if epic and dist(u.pos, hero.pos) <= 950.0:
            self.gain(7)
        elif u.kind in ('minion', 'monster'):
            self.gain(1)

    def any_death(self, hero, victim, killer):
        if victim.team != hero.team and hero.alive and dist(victim.pos, hero.pos) <= 950.0:
            self.gain(7)

    def died(self, hero):
        self.stacks = 0
        self.e = None

    def tick(self, hero, t):
        if self.stacks >= 7:
            self.try_roar()
        if self.e is not None and t > self.e['until'] and t > self.e.get('charged_until', 0.0):
            self.e = None

    # ------------------------------------------------------------------ spells
    def cast_begin(self, c):
        g = self.g
        name = c['inf'].name
        if name == 'Pulverize':
            g.at(g.t + 0.167, lambda t, c=c: self.hero.alive and self.q_hit(c))
        elif name == 'AlistarE':
            self.e = {'stacks': 0, 'until': g.t + (self.dv('AlistarE', 'Duration') or 5.0), 'ticks': set()}
        elif name == 'FerociousHowl':
            self.cleanse()
            pct = (self.dv('FerociousHowl', 'RDamageReduction') or 55.0) / 100.0
            self.hero.damage_reduction = (g.t + (self.dv('FerociousHowl', 'RDuration') or 7.0), pct)

    def resolve(self, c):
        name = c['inf'].name
        if name == 'Pulverize':
            return True                                  # its hit was scheduled from the cast's start
        if name == 'FerociousHowl':
            return True
        return False

    def q_hit(self, c):
        g, hero = self.g, self.hero
        from ..spells import info
        inf = info(hero.champ, 'Pulverize')
        amount = self.dv('Pulverize', 'BaseDamage') + 0.8 * hero.ap
        champs = 0
        for o in g.spells.enemies(hero):
            if dist(o.pos, hero.pos) <= 375.0 + o.radius:
                if c.get('tpl') is not None:
                    g.templates.on_cast_hit(c['tpl'], o)
                g.deal(hero, o, amount, P.MAGIC, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('Pulverize'))
                if o.alive:
                    g.spells.cc(hero, o, inf, 30, self.dv('Pulverize', 'KnockupDuration') or 1.0, stun=True, name_hash=KNOCKUP_Q)
                    champs += o.is_hero
        self.gain(champs)

    def spell_hit(self, c, tgt):
        g, hero = self.g, self.hero
        name = c['inf'].name
        if name == 'Headbutt':
            if dist(hero.pos, tgt.pos) > 400.0 + tgt.radius:
                return True
            from ..spells import info
            inf = info(hero.champ, 'Headbutt')
            g.deal(hero, tgt, self.dv('Headbutt', 'Damage') + hero.ap, P.MAGIC, basic=False, source=P.SRC_DIRECT,
                   spell_hash=P.elf('Headbutt'))
            if tgt.alive and not tgt.is_structure:
                o = c.get('origin') or hero.pos
                d = dist(o, tgt.pos) or 1.0
                back = self.dv('Headbutt', 'KnockBackDistance') or 700.0
                dest = (tgt.pos[0] + (tgt.pos[0] - o[0]) / d * back, tgt.pos[1] + (tgt.pos[1] - o[1]) / d * back)
                dest = g.nav.nearest_free(*dest) or tgt.pos
                g.spells.cc(hero, tgt, inf, 31, 0.5, stun=True, name_hash=KNOCK_W)
                g.spells.cc(hero, tgt, inf, 5, self.dv('Headbutt', 'StunDuration') or 0.75, stun=True)
                tgt.path = None
                g.q += g.pk.dash(g.t, tgt, [tgt.pos, dest], dist(tgt.pos, dest) / 0.5)
                g.at(g.t + 0.5, lambda t, tgt=tgt, dest=dest: setattr(tgt, 'pos', dest) if tgt.alive else None)
                if tgt.is_hero:
                    self.gain(1)
            return True
        return False

    # ------------------------------------------------------------------ Trample's charge
    def dealt(self, hero, tgt, dealt, basic, spell_hash, source=None):
        g = self.g
        if self.e is None or not tgt.is_hero or spell_hash != P.damage_hash('AlistarE'):
            return
        tick = round(g.t, 2)
        if tick in self.e['ticks'] or self.e['stacks'] >= 5:
            return
        self.e['ticks'].add(tick)
        self.e['stacks'] += 1
        if self.e['stacks'] >= 5:
            self.e['charged_until'] = g.t + (self.dv('AlistarE', 'FullChargeDuration') or 5.0)

    def after_attack(self, hero, tgt, dealt):
        g = self.g
        if self.e is None or self.e.get('charged_until', 0.0) < g.t or not tgt.is_hero or not tgt.alive:
            return
        from ..spells import info
        inf = info(hero.champ, 'AlistarE')
        g.deal(hero, tgt, 20.0 + 15.0 * (min(18, hero.level) - 1), P.MAGIC, basic=False, source=P.SRC_DIRECT,
               spell_hash=P.elf('AlistarEAttack'))
        if tgt.alive:
            g.spells.cc(hero, tgt, inf, 5, self.dv('AlistarE', 'StunDuration') or 1.0, stun=True)
            self.gain(1)
        zc = getattr(hero, 'zone_ctx', None)
        if zc is not None:
            zc['stop'] = True                            # [wiki] the stun ends Trample's effects
        self.e = None

    # ------------------------------------------------------------------ Unbreakable Will
    def cleanse(self):
        g, hero = self.g, self.hero
        hero.cc_until = hero.root_until = g.t
        hero.silence_until = hero.disarm_until = g.t
        hero.forced_until = 0.0
        for key, b in list(getattr(hero, 'buff_list', {}).items()):
            if b.get('args') and b['args'][2] in CC_TYPES:
                hero.buff_list.pop(key, None)
                if b.get('undo'):
                    b['undo']()
                if b.get('known', True):
                    g.tell_all(g.pk.buff_remove(hero.net, b['slot'], b['hash']))
        hero.slows = {}
        g.spells.respeed(hero)
        g.spells.action_state(hero)


KIT = Alistar
