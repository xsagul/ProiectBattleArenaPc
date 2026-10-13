"""Champion kits written one champion at a time (docs/CHAMPIONS16.md): what the wiki says each spell and passive does,
checked against the game's 16.20 data (its numbers win) and the replays (timings, names, who is hit), played by our
server. A kit owns the parts of its champion the generic spell engine (spells.py) gets wrong; everything it does not
take over stays generic, and the templates still send the real server's own packets of each cast.

Hooks the engine calls (a kit defines only what it needs):
  resolve(c) -> True          the cast time is over: the kit plays the spell's effect (spells.resolve)
  spell_hit(c, tgt) -> True   a spell of the champion hits a unit: the kit deals its damage / effects (spells.hit)
  attack_start(hero, tgt)     a basic attack begins (units.start_attack)
  attack_hit(hero, tgt, amount) -> amount    a basic attack lands, before its damage (game.basic_hit)
  after_attack(hero, tgt, dealt)             after its damage
  dealt(hero, tgt, dealt, basic, spell_hash) the champion damaged a unit (game.deal)
  takedown(hero, victim)      the champion killed or assisted on an enemy champion (game.hero_killed)
  died(hero) / respawned(hero)
  tick(hero, t)               every frame
"""
import importlib
import os


class Kit:
    def __init__(self, game, hero):
        self.g, self.hero = game, hero

    @staticmethod
    def h(hexname):
        """a name hash as the replays print it (little-endian hex) -> int"""
        return int.from_bytes(bytes.fromhex(hexname), 'little')


_mods = {}


def module(name):
    if name not in _mods:
        try:
            _mods[name] = importlib.import_module(f'.{name.lower()}', __name__)
        except ModuleNotFoundError:
            _mods[name] = None
    return _mods[name]


class Kits:
    def __init__(self, game):
        self.g = game
        self.by_net = {}

    def of(self, unit):
        if unit is None or not getattr(unit, 'is_hero', False):
            return None
        k = self.by_net.get(unit.net, False)
        if k is False and os.environ.get('BA_NO_KITS'):          # measuring without them
            k = self.by_net[unit.net] = None
        if k is False:
            m = module(unit.name)
            k = m.KIT(self.g, unit) if m is not None and hasattr(m, 'KIT') else None
            self.by_net[unit.net] = k
        return k

    def call(self, unit, hook, *args):
        k = self.of(unit)
        f = getattr(k, hook, None) if k is not None else None
        return f(*args) if callable(f) else None

    def tick(self, t, dt):
        for h in self.g.heroes:
            k = self.of(h)
            if k is not None and hasattr(k, 'tick'):
                k.tick(h, t)


def setup(game, session=None):
    game.kits = Kits(game)
    game.systems.append(game.kits.tick)
