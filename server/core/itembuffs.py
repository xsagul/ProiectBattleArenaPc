"""Buffs given by item and rune passives [m: tools/buff_trigger16.py, 40 replays]: an item's or rune's buff goes on the
unit its holder hits (or on the holder itself) at the measured trigger - its basic attack or spell damaging a unit,
any hit, or the holder taking damage from a champion - when the buff is not on already and its usual gap since the last
one (the replays' 10th percentile) has passed; with its measured type, duration and count. Its renewals, effects and
sounds then follow by the buff hooks (renewals / effects / sounds).

Not here: champions' buffs (the templates give them at their casts' hits); buffs no single item / rune explains.
The damage some of them deal (the burns) is not played yet.
"""
import json
import os

from . import gamedata as G
from . import packets as P

_table = None


def table():
    global _table
    if _table is None:
        if os.environ.get('BA_NO_ITEM_BUFFS'):          # measuring without them
            _table = {}
            return _table
        try:
            raw = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'buff_trigger16.json')))
        except Exception:
            raw = {}
        _table = {h: r for h, r in raw.items() if r['owner'].startswith(('item:', 'rune:')) and r['explains'] >= 0.7}
    return _table


class ItemBuffs:
    def __init__(self, game):
        self.g = game
        self.last = {}                   # (caster, holder, hash) -> time of the last application
        self._rules = {}                 # hero net -> (inventory + perks key, [rules])

    def rules(self, hero):
        tips = getattr(self.g, 'tooltips', None)
        perks = tuple(tips.perks(hero)) if tips is not None else ()
        key = (tuple(hero.inventory), perks)
        cached = self._rules.get(hero.net)
        if cached is not None and cached[0] == key:
            return cached[1]
        items = {i for i in hero.inventory if i is not None}
        out = []
        for h, r in table().items():
            kind, ident = r['owner'].split(':')
            if (kind == 'item' and int(ident) in items) or (kind == 'rune' and int(ident) in perks):
                out.append((h, r))
        self._rules[hero.net] = (key, out)
        return out

    def give(self, holder, caster, h, r):
        g, sp = self.g, self.g.spells
        if sp is None or not holder.alive:
            return
        key = ('item_buff', h)
        if not hasattr(holder, 'buff_list'):
            holder.buff_list = {}
        if key in holder.buff_list:
            return                                       # on already: its renewals come from core/renewals.py
        k = (caster.net, holder.net, h)
        if g.t - self.last.get(k, -1e9) < r['cooldown']:
            return
        self.last[k] = g.t
        hh = int.from_bytes(bytes.fromhex(h), 'little')
        slot = sp.buff_slot(holder)
        dur = r['dur'] if 0 < r['dur'] < 1000 else 3600.0
        known = g.vision is None or not g.vision.hidden(holder)
        holder.buff_list[key] = {'slot': slot, 'until': g.t + dur, 'hash': hh, 'undo': None, 'known': known,
                                 'args': (caster.net, slot, r['type'], hh, 0)}
        if known:
            g.q += g.pk.buff_add(holder.net, caster.net, slot, r['type'], hh, r['dur'], count=r.get('count', 1))
        sp.buffs.append([g.t + dur, holder, key])

    def on_damage(self, src, tgt, basic):
        """src damaged tgt (game.deal)"""
        if src is not None and src.is_hero and src is not tgt:
            for h, r in self.rules(src):
                trig = r['trigger']
                if trig == 'hurt' or trig == 'attack':
                    continue
                if (trig == 'basic_hit' and not basic) or (trig == 'spell_hit' and basic):
                    continue
                if r.get('champions_only') and not tgt.is_hero:
                    continue
                self.give(tgt if r['on'] == 'target' else src, src, h, r)
        if tgt.is_hero and src is not None and src.is_hero and src.team != tgt.team:
            for h, r in self.rules(tgt):
                if r['trigger'] == 'hurt':
                    self.give(tgt, tgt, h, r)          # [a] taking damage from an enemy champion

    def on_attack(self, hero, tgt):
        for h, r in self.rules(hero):
            if r['trigger'] == 'attack' and (not r.get('champions_only') or tgt.is_hero):
                self.give(tgt if r['on'] == 'target' else hero, hero, h, r)


def setup(game, session=None):
    game.itembuffs = ItemBuffs(game)
