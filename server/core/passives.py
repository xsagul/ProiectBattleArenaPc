"""Champion passives. No general rule exists for them: each is its own script on Riot's server, and the client holds
none. What is here are the passives whose whole rule is "a basic attack deals bonus damage" under one of a few plain
conditions, with the amounts read from the LoL wiki's text (gamedata.wiki(champion, 'P'): "N : M (based on level)
(+ x% AP) bonus magic damage") - every other passive is still to be written, one champion at a time.

Kinds (KINDS below says which champion has which; the wiki's own words in brackets):
  onhit         every basic attack                                       [Locke, Orianna]
  after_spell   the next basic attack within some seconds of a cast      [Zoe 5 s]  (Akali: core/kits/akali.py)
  spell_count   the basic attack after every n-th cast                   [Sona: 3]
  periodic      a basic attack, once every some seconds                  [Ziggs: 12 s]
  per_target    a basic attack, once every some seconds per target       [Nautilus: 6 s - a: its root is left out]
  mark          a basic attack on a unit a spell hit in the last seconds [Lux: 6 s]
[a] the amount grows evenly from level 1 to 18 between the wiki's two numbers (the wiki's own curve is not linear for
all of them).
"""
import re

from . import gamedata as G
from . import packets as P

KINDS = {'Locke': ('onhit', 0.0), 'Orianna': ('onhit', 0.0), 'Zoe': ('after_spell', 5.0),
         'Sona': ('spell_count', 3), 'Ziggs': ('periodic', 12.0), 'Nautilus': ('per_target', 6.0), 'Lux': ('mark', 6.0)}
AMOUNT = re.compile(r'deal[s]? (?:an additional )?(\d+(?:\.\d+)?)(?: (?:−|-|:|to) (\d+(?:\.\d+)?))?(?: \(based on level\))?'
                    r'((?: \(\+ [\d.]+% (?:bonus )?A[DP]\))*) bonus (magic|physical|true) damage', re.I)
RATIO = re.compile(r'\(\+ ([\d.]+)% (bonus AD|AD|AP)\)', re.I)
TYPE = {'physical': P.PHYSICAL, 'magic': P.MAGIC, 'true': P.TRUE}


class Passives:
    def __init__(self, game):
        self.g = game
        self.rules = {}                  # champion -> (kind, argument, lo, hi, [(share, stat)], damage type) | None

    def rule(self, name):
        if name not in self.rules:
            r = None
            kind = KINDS.get(name)
            text = ((G.wiki(name, 'P') or {}).get('text') or '') if kind else ''
            m = AMOUNT.search(text)
            if kind and m:
                lo = float(m.group(1))
                hi = float(m.group(2)) if m.group(2) else lo
                ratios = [(float(a) / 100.0, b.lower()) for a, b in RATIO.findall(m.group(3) or '')]
                r = (kind[0], kind[1], lo, hi, ratios, TYPE[m.group(4).lower()])
            self.rules[name] = r
        return self.rules[name]

    def amount(self, hero, r):
        v = r[2] + (r[3] - r[2]) * (max(1, min(18, hero.level)) - 1) / 17.0
        for share, of in r[4]:
            v += share * (hero.ap if of == 'ap' else hero.bonus['ad'] if of == 'bonus ad' else hero.base_ad + hero.bonus['ad'])
        return v

    # ------------------------------------------------------------------ what the spell engine and the game tell
    def on_cast(self, hero, slot):
        r = self.rule(hero.name)
        if r is None or slot > 3:
            return
        if r[0] == 'after_spell':
            hero.passive_until = self.g.t + r[1]
        elif r[0] == 'spell_count':
            hero.passive_count = getattr(hero, 'passive_count', 0) + 1

    def on_spell_hit(self, hero, tgt):
        r = self.rule(hero.name)
        if r is not None and r[0] == 'mark':
            tgt.passive_marks = getattr(tgt, 'passive_marks', {})
            tgt.passive_marks[hero.net] = self.g.t + r[1]

    def on_basic_hit(self, hero, tgt):
        r = self.rule(hero.name)
        if r is None or not tgt.alive or tgt.is_structure:
            return
        g, t = self.g, self.g.t
        kind = r[0]
        if kind == 'after_spell':
            if t > getattr(hero, 'passive_until', 0.0):
                return
            hero.passive_until = 0.0
        elif kind == 'spell_count':
            if getattr(hero, 'passive_count', 0) < r[1]:
                return
            hero.passive_count = 0
        elif kind == 'periodic':
            if t < getattr(hero, 'passive_ready', 0.0):
                return
            hero.passive_ready = t + r[1]
        elif kind == 'per_target':
            seen = hero.__dict__.setdefault('passive_targets', {})
            if t < seen.get(tgt.net, 0.0):
                return
            seen[tgt.net] = t + r[1]
        elif kind == 'mark':
            marks = getattr(tgt, 'passive_marks', {})
            if t > marks.get(hero.net, 0.0):
                return
            marks.pop(hero.net, None)
        amount = self.amount(hero, r)
        if hero.name == 'Locke':
            # [the wiki] up to twice as much by the target's missing health, the most at 70 % missing
            missing = 1.0 - tgt.hp / max(1.0, tgt.max_hp)
            amount *= 1.0 + min(1.0, missing / 0.7)
        if amount > 0:
            # [m: the replays' damage] a passive's bonus names the passive (QiyanaPassive, SylasPassive)
            name = str(getattr(hero.champ, 'passive', '') or f'{hero.name}Passive').split('/')[-1]
            g.deal(hero, tgt, amount, r[5], basic=False, source=P.SRC_DIRECT, spell_hash=P.damage_hash(name))


def setup(game, session=None):
    game.passives = Passives(game)
