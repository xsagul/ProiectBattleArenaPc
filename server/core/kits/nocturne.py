"""Nocturne - what the generic engine and the templates leave out (docs/CHAMPIONS16.md: not done as a whole yet).

Duskbringer's trail [m: 2 replays, ~1,000 a match]: 0.27 s after the cast the trail's buff 2579080d (type 1, 0.5 s) is
given and renewed (282) on every update of his script while he is on the trail - 5.3 - 5.6 s [a: the trail's 5 s
life; leaving it early is not modelled].
"""
from . import Kit
from .. import packets as P

TRAIL = 0x0d087925
TRAIL_LIFE = 5.5


class Nocturne(Kit):
    def cast_begin(self, ctx):
        if getattr(ctx.get('inf'), 'name', '') != 'NocturneDuskbringer':
            return
        g = self.g
        until = g.t + 0.27 + TRAIL_LIFE

        def start(t):
            h = self.hero
            if not h.alive or g.spells is None:
                return
            if not hasattr(h, 'buff_list'):
                h.buff_list = {}
            key = ('kit', 'nocturne_trail')
            b = h.buff_list.get(key)
            if b is None:
                slot = g.spells.buff_slot(h)
                b = h.buff_list[key] = {'slot': slot, 'until': t + 0.5, 'hash': TRAIL, 'undo': None, 'known': True,
                                        'args': (h.net, slot, 1, TRAIL, 0)}
                g.q += g.pk.buff_add(h.net, h.net, slot, 1, TRAIL, 0.5)
                g.spells.buffs.append([b['until'], h, key])

                def renew(t2):
                    cur = h.buff_list.get(key)
                    if cur is not b or not h.alive or t2 >= self.trail_until:
                        return
                    b['until'] = t2 + 0.5
                    from ..renewals import handles
                    if not handles(TRAIL):
                        g.q += g.pk.buff_count(h.net, b['slot'], h.net, 0.5, 1)
                    g.spells.buffs.append([b['until'], h, key])
                    g.after_frames(8, renew)
                g.after_frames(8, renew)
        self.trail_until = until
        g.at(g.t + 0.27, start)


KIT = Nocturne
