"""Script sounds (211) that ride with buffs [m: tools/buff_sfx16.py, 40 replays, 182 buffs]: when a buff is given or
taken away, the real server plays the sound events its scripts name ("Play_sfx_Perks_Resolve_BonePlating_
OnBuffActivate", "Stop_sfx_Rell_RellE_buffactivate") on the buff's holder or caster, from that unit's sound bank.

211 [m]: +0x40 the event's name, +0x60 the bank (a character name), +0x70 the unit, +0x98 a number as recorded; the
other fields empty / 0.
"""
import json
import os

from . import gamedata as G
from . import packets as P
from .units import FRAME

_table = None


def table():
    global _table
    if _table is None:
        try:
            _table = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'buff_sfx16.json')))
        except Exception:
            _table = {}
    return _table


def hx(s):
    return s.encode().hex()


class Sounds:
    def __init__(self, game):
        self.g = game
        self.live = {}                   # (holder, slot) -> (buff hash hex, caster net)

    def play(self, e, holder_net, caster_net):
        g = self.g
        unit = g.units.get(holder_net if e['on'] == 'holder' else caster_net)
        if unit is None or (g.vision is not None and g.vision.hidden(unit)):
            return
        bank = unit.name if e['bank'] == 'unit' else e['bank']
        v = {'+0x10': '00000000', '+0x18': {'text': ''}, '+0x28': '00000000', '+0x30': {'text': ''},
             '+0x40': {'text': hx(e['name'])}, '+0x50': {'text': ''}, '+0x60': {'text': hx(bank)},
             '+0x70': P.u32(unit.net), '+0x78': {'text': ''}, '+0x88': {'text': ''}, '+0x98': P.u32(e['num'])}
        body = g.pk.enc(211, v)
        if e.get('delay'):
            g.at(g.t + e['delay'] * FRAME, lambda t: g.q.append((1, 211, 0, body)))
        else:
            g.q.append((1, 211, 0, body))

    def on_buff_add(self, tgt_net, caster_net, slot, name_hash):
        self.on_buff_remove(tgt_net, slot)
        h = P.u32(name_hash)
        r = table().get(h)
        if r is None:
            return
        self.live[(tgt_net, slot)] = (h, caster_net)
        for e in r['add']:
            self.play(e, tgt_net, caster_net)

    def on_buff_remove(self, tgt_net, slot):
        x = self.live.pop((tgt_net, slot), None)
        if x is None:
            return
        for e in table()[x[0]]['remove']:
            self.play(e, tgt_net, x[1])


def setup(game, session=None):
    game.sounds = Sounds(game)
    game.pk.buff_hooks.append(game.sounds)
