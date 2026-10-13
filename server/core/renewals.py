"""Buff renewals (282 NPC_BuffUpdateCount) as Riot's server sends them [m: tools/buff_renew16.py, 40 replays, 132 buffs]:
a buff is renewed by what its scripts listen to - its caster's attack (at the windup's end: a fixed number of frames
after the attack began), basic hit, spell hit or cast, its holder taking damage - or on every script update (8 frames
after the last renewal). Each 282 sets the measured duration and the buff's count (its counter when it stacks).

Every buff the server gives is seen here (packets.buff_hooks: buff_add, the templates' 435s, buff_remove, counters).
Buffs core/spells.py renews on its own table (buff_refresh16) are left to it when this table does not know them.
"""
import json
import os

from . import gamedata as G
from .units import FRAME

_table = None


def table():
    global _table
    if _table is None:
        try:
            _table = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'buff_renew16.json')))
        except Exception:
            _table = {}
    return _table


def handles(name_hash):
    """the buff's 282s are this module's (its measured causes): a system that keeps such a buff on only extends it"""
    from . import packets as P
    return P.u32(name_hash) in table()


class Renewals:
    def __init__(self, game):
        self.g = game
        self.live = {}                   # (holder, slot) -> {'rule', 'caster', 'count', 'last'}
        self.by_caster = {}              # caster net -> set of (holder, slot)
        self.by_holder = {}

    # ------------------------------------------------------------------ buff hooks (packets.buff_hooks)
    def on_buff_add(self, tgt_net, caster_net, slot, name_hash):
        self.on_buff_remove(tgt_net, slot)
        from . import packets as P
        rule = table().get(P.u32(name_hash))
        if rule is None:
            return
        k = (tgt_net, slot)
        self.live[k] = {'rule': rule, 'caster': caster_net, 'count': rule['count'], 'last': self.g.t}
        self.by_caster.setdefault(caster_net, set()).add(k)
        self.by_holder.setdefault(tgt_net, set()).add(k)

    def on_buff_remove(self, tgt_net, slot):
        b = self.live.pop((tgt_net, slot), None)
        if b is not None:
            self.by_caster.get(b['caster'], set()).discard((tgt_net, slot))
            self.by_holder.get(tgt_net, set()).discard((tgt_net, slot))

    def on_buff_counter(self, tgt_net, slot, count):
        b = self.live.get((tgt_net, slot))
        if b is not None and b['rule'].get('counts', 1) > 1:
            b['count'] = count                               # a stacking buff's 282 carries its stacks

    # ------------------------------------------------------------------ events
    def renew(self, k):
        b = self.live.get(k)
        if b is None:
            return
        g = self.g
        holder = g.units.get(k[0])
        if holder is None or not holder.alive:
            return
        b['last'] = g.t
        if g.vision is not None and g.vision.hidden(holder):
            return
        g.q += g.pk.buff_count(k[0], k[1], b['caster'], b['rule']['dur'], b['count'])

    def event(self, cause, caster=None, holder=None, other=None):
        """an event of a buff's caster (about `other`: the unit it attacked / hit) or of its holder (hurt). A rule's
        cause may be scoped: '<cause>@holder' only when the event is about the buff's holder, '@hero' a champion"""
        keys = self.by_caster.get(caster.net, ()) if caster is not None else self.by_holder.get(holder.net, ())
        for k in list(keys):
            b = self.live.get(k)
            if b is None:
                continue
            causes = b['rule']['causes']
            d = None
            if cause in causes:
                d = causes[cause]
            elif other is not None and other.net == k[0] and other.net != b['caster'] and f'{cause}@holder' in causes:
                d = causes[f'{cause}@holder']
            elif other is not None and other.is_hero and f'{cause}@hero' in causes:
                d = causes[f'{cause}@hero']
            if d is None:
                continue
            if d:
                self.g.at(self.g.t + d * FRAME, lambda t, k=k: self.renew(k))
            else:
                self.renew(k)

    def on_attack(self, unit, tgt=None):
        if unit.net in self.by_caster:
            self.event('attack', caster=unit, other=tgt)

    def on_damage(self, src, tgt, basic):
        if src is not None and src.net in self.by_caster:
            self.event('basic_hit' if basic else 'spell_hit', caster=src, other=tgt)
        if tgt.net in self.by_holder:
            self.event('hurt', holder=tgt)

    def on_cast(self, hero):
        if hero.net in self.by_caster:
            self.event('cast', caster=hero)

    def tick(self, t, dt):
        from .game import SCRIPT_UPDATE
        for k, b in list(self.live.items()):
            # a meter (many counts: Kindred's Hunter's Vigor 0 - 100) is renewed when its value changes, not on every
            # update [m: its 282s come while it grows] - not played until the meter is
            if b['rule'].get('counts', 1) > 3:
                continue
            causes = b['rule']['causes']
            if 'tick' in causes and t - b['last'] >= SCRIPT_UPDATE - 1e-6:
                self.renew(k)
            elif 'frame' in causes and t - b['last'] >= max(1, causes['frame']) * FRAME - 1e-6:
                self.renew(k)


def setup(game, session=None):
    game.renewals = Renewals(game)
    game.pk.buff_hooks.append(game.renewals)
    game.systems.append(game.renewals.tick)
