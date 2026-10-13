"""Buffs a champion holds while a condition holds (a passive, an item) [m: tools/self_buffs16.py -> self_buffs16.json]:
on the champion's script updates (every 0.267 s) the condition is looked at; while it holds the buff is given (435 the
first time) and renewed (282 with its duration); when it stops, the buff runs out by itself (262).
  always       whenever the champion lives (a passive's counter: Ahri, Kindred)
  unseen       the enemy team does not see it (3179_UnseenBuff)
  combat_hero  it dealt or took champion damage in the last 3 s;  combat_any  any damage in the last 3 s
  combat_hero5 / combat_any5  the same over 5 s (AatroxInCombat)
Owner: a champion's name, or 'item:<id>' (any champion holding that item).
"""
import json
import os

from . import gamedata as G
from . import packets as P

COMBAT = 3.0
# Umbral Glaive (3179) [m: replay 4012465086 Talon, ~1,100 139s a holder]: while the enemy team does not see its holder,
# 3179_UnseenBuff (type 1, 1 s, renewed by 282 on every update); 0.8 s into it 3179_AttackReady (type 2, 4 s), replaced
# (139 BuffReplace, 4 s) on every update while still unseen; both run out by themselves once seen
UNSEEN, ATTACK_READY = P.elf('3179_UnseenBuff'), P.elf('3179_AttackReady')


def table():
    try:
        return json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'self_buffs16.json')))
    except Exception:
        return {}


class CondBuffs:
    def __init__(self, game):
        self.g = game
        self.table = table()
        self.started = set()

    def owns(self, h, owner):
        if owner.startswith('item:'):
            return int(owner[5:]) in [i for i in getattr(h, 'inventory', []) if i]
        return h.name == owner

    def holds(self, h, cond):
        g = self.g
        if cond == 'always':
            return True
        if cond == 'unseen':
            enemy = g.visions.get(200 if h.team == 100 else 100) if getattr(g, 'visions', None) else None
            return enemy is not None and enemy.hidden(h)
        last = getattr(h, 'last_hero_damage' if cond.startswith('combat_hero') else 'last_damage', -99.0)
        return g.t - last < (5.0 if cond.endswith('5') else COMBAT)

    def tick(self, t, dt):
        g = self.g
        for h in g.heroes:
            if h.net not in self.started:
                self.started.add(h.net)
                g.script_timer(0.26729, lambda t2, h=h: self.update(h), first=True, alive=lambda: not g.over)

    def umbral(self, h):
        g, sp = self.g, self.g.spells
        if 3179 not in [i for i in getattr(h, 'inventory', []) if i]:
            return
        enemy = g.visions.get(200 if h.team == 100 else 100) if getattr(g, 'visions', None) else None
        if enemy is None or not enemy.hidden(h):
            h.unseen_since = None
            return
        if getattr(h, 'unseen_since', None) is None:
            h.unseen_since = g.t
        if not hasattr(h, 'buff_list'):
            h.buff_list = {}
        for key, hh, btype, dur, after in ((('umbral', 0), UNSEEN, 1, 1.0, 0.0), (('umbral', 1), ATTACK_READY, 2, 4.0, 0.8)):
            if g.t - h.unseen_since < after - 1e-6:
                continue
            b = h.buff_list.get(key)
            if b is None:
                slot = sp.buff_slot(h)
                b = h.buff_list[key] = {'slot': slot, 'until': g.t + dur, 'hash': hh, 'undo': None, 'known': True,
                                        'args': (h.net, slot, btype, hh, 0)}
                g.q += g.pk.buff_add(h.net, h.net, slot, btype, hh, dur)
            else:
                b['until'] = g.t + dur
                if hh == UNSEEN:
                    g.q += g.pk.buff_count(h.net, b['slot'], h.net, dur, 1)
                else:
                    g.q.append((1, 139, h.net, g.pk.enc(139, {'+0x10': P.f32(dur), '+0x14': P.f32(0.0),
                                                                 '+0x18': P.u32(h.net), '+0x1c': f"{b['slot']:02x}"})))
            sp.buffs.append([b['until'], h, key])

    def update(self, h):
        g, sp = self.g, self.g.spells
        if sp is None or not h.alive:
            return
        self.umbral(h)
        for hh, r in self.table.items():
            if not self.owns(h, r['owner']) or not self.holds(h, r['cond']):
                continue
            key = ('cond', hh)
            if not hasattr(h, 'buff_list'):
                h.buff_list = {}
            b = h.buff_list.get(key)
            dur = float(r['dur'])
            name_hash = int.from_bytes(bytes.fromhex(hh), 'little')
            if b is None:
                slot = sp.buff_slot(h)
                b = h.buff_list[key] = {'slot': slot, 'until': g.t + dur, 'hash': name_hash, 'undo': None, 'known': True,
                                        'args': (h.net, slot, r['type'], name_hash, 0)}
                g.q += g.pk.buff_add(h.net, h.net, slot, r['type'], name_hash, dur)
                sp.buffs.append([b['until'], h, key])
            elif dur < 1000:
                b['until'] = g.t + dur
                g.q += g.pk.buff_count(h.net, b['slot'], h.net, dur, 1)
                sp.buffs.append([b['until'], h, key])


def setup(game, session=None):
    game.condbuffs = CondBuffs(game)
    game.systems.append(game.condbuffs.tick)
