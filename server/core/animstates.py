"""Animation overrides a champion's scripts set on every script update (904) [m: tools/anim_states16.py ->
anim_states16.json]: for the champions whose 904 is a steady stream (Xin Zhao, Sivir, Garen, Senna; Aatrox has his own
rule in core/kits/aatrox.py), on each update of the champion's script the content that goes with the buffs it holds
(the most specific rule whose buffs it has all), else the default content.
"""
import json
import os

from . import gamedata as G

OWN = {'Aatrox'}            # their kits send their 904s


def table():
    try:
        return json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'anim_states16.json')))
    except Exception:
        return {}


def h32(x):
    return int.from_bytes(bytes.fromhex(x), 'little')


class AnimStates:
    def __init__(self, game):
        self.g = game
        self.table = {c: r for c, r in table().items() if c not in OWN and r.get('stream', 0) >= 0.5}
        self.started = set()

    def tick(self, t, dt):
        for h in self.g.heroes:
            if h.net not in self.started and h.name in self.table:
                self.started.add(h.net)
                self.g.script_timer(0.0, lambda t2, h=h: self.update(h), alive=lambda: not self.g.over)

    def update(self, h):
        if not h.alive:
            return
        r = self.table[h.name]
        have = {b.get('hash') for b in getattr(h, 'buff_list', {}).values()}
        content = r['default']
        for keys, c in r['rules']:
            if all(h32(k) in have for k in keys):
                content = c
                break
        if content:
            self.g.q += self.g.pk.anim_states(h.net, [(h32(a), h32(b)) for a, b in content])


def setup(game, session=None):
    game.animstates = AnimStates(game)
    game.systems.append(game.animstates.tick)
