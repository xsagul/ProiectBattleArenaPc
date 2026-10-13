"""The engine side of Riot's AI scripts: what the functions their Lua calls do in our match.

A unit with an AI script (a camp monster: data/scripts/leashy of the 16.20 client) gets its own Lua state (luavm.VM):
the script's globals are that unit's (GetThis, GetState, its timers, its CharVars), as in Riot's engine, where each AI
script instance runs in the unit's environment. The engine calls into the script on its events:

    OnInit()                                 when the unit is made
    LeashedCallForHelp(caller, attacker)     a unit of its camp (or itself) was hit by attacker [a: our reading of the
                                             name; Leashy's own code then decides whether to answer]
    OnTargetLost(reason, target)             its target died / became invalid
    <timer name>()                           a timer set by InitTimer, every 'delay' seconds while it runs

Everything the script decides (whom to attack, when to give up, when to go home, its frustration buffs) is Riot's
code; this file only answers its questions about the world (distances, targets, health, tags) and carries out its
orders (attack, move, set health). A function the scripts use but this file does not supply is reported, by name,
in AIHost.missing (the census of what is left: tools/lua_api_census.py lists them all ahead of time).

What the engine itself does beside the scripts stays measured in ai.py / game.py (the 586 leash packets, the reset
regeneration's 699 events every second frame).
"""
import math
import os

from . import gamedata as G
from . import packets as P
from .luavm import VM, LuaError, MultiReturn
from .units import dist

SCRIPTS = os.path.join(G.ROOT, 'data', 'lua1620', 'scripts')
# the folders DoLuaShared / DoLuaLevel look in [the file names of the 16.20 manifest]
SHARED_DIRS = ('data__shared__scripts__', 'data__scripts__', 'data__buildingblocks__', 'data__shared__scripts__aicomponents__',
               'data__shared__')
LEVEL_DIRS = ('levels__map11__scripts__',)

# engine enums the scripts only compare with each other [our numbering: the scripts never print or send them]
AI_STATES = ['AI_IDLE', 'AI_ATTACK', 'AI_RETREAT', 'AI_HALTED', 'AI_TAUNTED', 'AI_BERSERK', 'AI_FEARED', 'AI_FLEEING',
             'AI_CHARMED', 'AI_MOVE', 'AI_GUARD', 'AI_STANDING', 'AI_ATTACKMOVESTATE', 'AI_ATTACKMOVE_ATTACKING',
             'AI_PET_IDLE', 'AI_PET_MOVE', 'AI_PET_ATTACK', 'AI_PET_HOLDPOSITION', 'AI_PET_RETURN', 'AI_SIEGEATTACK',
             'AI_FOLLOW', 'AI_CAST', 'AI_SOFTATTACK', 'AI_ATTACK_GOING_TO_LAST_KNOWN_LOCATION']
ORDERS = ['ORDER_NONE', 'ORDER_HOLD', 'ORDER_MOVETO', 'ORDER_ATTACKUNIT', 'ORDER_TEMPCASTSPELL', 'ORDER_PETHARDSTOP',
          'ORDER_MOVETO_SAFE', 'ORDER_ORDERNONE', 'ORDER_ATTACKTO', 'ORDER_STOP', 'ORDER_TAUNT', 'ORDER_ATTACKMOVE']
STOP_REASONS = ['STOPREASON_IMMEDIATELY', 'STOPREASON_MOVING', 'STOPREASON_TARGET_LOST', 'STOPREASON_TARGET_DEAD']
CONSTANTS = {n: i for i, n in enumerate(AI_STATES)}
CONSTANTS.update({n: i for i, n in enumerate(ORDERS)})
CONSTANTS.update({n: i + 1 for i, n in enumerate(STOP_REASONS)})
CANCEL_SLACK = 100.0             # [a] TargetInCancelAttackRange: the attack is kept while the target is this much beyond reach


def fnv1a(s):
    h = 0x811c9dc5
    for b in s.lower().encode():
        h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h


class Point:
    """a place as the scripts hold it (Make3DPoint, GetMyPos ...)"""
    __slots__ = ('x', 'y', 'z')

    def __init__(self, x, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    @property
    def pos(self):
        return (self.x, self.z)


def script_path(name, dirs):
    low = name.lower()
    if low.endswith('.lua'):
        low = low[:-4]
    for d in dirs:
        p = os.path.join(SCRIPTS, d + low + '.luabin64')
        if os.path.exists(p):
            return p
    return None


def unit_tags(u):
    """the unit's tags (its record's unitTagsString; a champion's: Champion)"""
    tags = getattr(u, 'unit_tags', None)
    if tags is not None:
        return tags
    if u.is_hero:
        tags = {'Champion'}
    else:
        s = (u.base or {}).get('tags_string') or ''
        if not s and u.kind == 'monster':
            try:
                import bin_tree as BT
                ch = u.name.split('.')[0].lower()
                for e in BT.entries(G.MAP_WAD, f'data/characters/{ch}/{ch}.bin'):
                    if e[1] == 'CharacterRecord':
                        s = e[2].get('unitTagsString') or ''
                        break
            except Exception:
                s = ''
        tags = {t.strip() for t in s.split('|') if t.strip()}
        if not tags:
            tags = {'Minion', 'Minion_Lane'} if u.kind == 'minion' else {'Structure'} if u.is_structure else {'Monster'} \
                if u.kind == 'monster' else set()
    u.unit_tags = tags
    return tags


class AIHost:
    def __init__(self, game, unit, script):
        self.g, self.u = game, unit
        self.script = script
        self.state = CONSTANTS['AI_IDLE']
        self.roam = 0
        self.original_roam = 0
        self.target = None
        self.auto_attack = False
        self.timers = {}              # name -> [delay, repeat, running, next]
        self.vars = {}
        self.leash_counter = 0
        self.leash_pos = Point(unit.pos[0], 0.0, unit.pos[1])
        self.missing = {}             # engine name the script called that we do not supply -> count
        self.loaded = set()
        self.vm = VM()
        self.dead = False
        self._install()
        path = script_path(script, ('data__scripts__',))
        self.vm.load_file(path)
        self.tag_names = {}
        tags = self.vm.global_('UnitTagIndicies') or {}
        for name, idx in tags.items():
            self.tag_names[idx] = name
        self.call('OnInit')

    # ------------------------------------------------------------------ running the script
    def call(self, name, *args):
        try:
            return self.vm.call(name, *args)
        except LuaError as e:
            self.g.log(f'lua {self.script} {self.u.name} {name}: {e}')
            return None

    def tick(self, t):
        if self.dead:
            return
        for name, tm in list(self.timers.items()):
            if tm[2] and t >= tm[3] - 1e-9:
                tm[3] = t + tm[0]
                if not tm[1]:
                    tm[2] = False
                self.call(name)
        tgt = self.target
        u = self.u
        if tgt is not None and (not tgt.alive or not tgt.targetable):
            self.target = None
            u.target = None
            self.call('OnTargetLost', CONSTANTS['STOPREASON_TARGET_LOST'], tgt)
            tgt = self.target
        if tgt is not None and (self.auto_attack or self.state == CONSTANTS['AI_ATTACK']):
            u.target = tgt.net               # chasing (auto attack off while moving): the engine still follows it
        elif not self.auto_attack:
            u.target = None
        if self.state == CONSTANTS['AI_ATTACK'] and tgt is not None and not u.in_reach(tgt):
            if not u.path or dist(u.path[-1], tgt.pos) > 60.0:
                self.walk(tgt.pos)

    def close(self):
        self.dead = True
        self.vm.close()

    # ------------------------------------------------------------------ the engine's functions
    def walk(self, place):
        u, g = self.u, self.g
        if g.nav.line_clear(u.pos, place):
            u.go([place])
        else:
            u.path_to(place)

    def _install(self):
        vm, g, u = self.vm, self.g, self.u
        for k, v in CONSTANTS.items():
            vm.set_global(k, v)
        vm.set_global('owner', None)
        # anything the script calls that no one supplied: reported by name, an empty function in its place
        vm.register('EngineMissing', lambda name: self.missing.__setitem__(name, self.missing.get(name, 0) + 1))
        vm.load("""
setmetatable(_G, {__index = function(t, k)
    if type(k) == 'string' and string.match(k, '^%u%l') then
        local f = function(...) EngineMissing(k) return nil end
        return f
    end
    return nil
end})""", 'missing')
        fns = {
            # scripts
            'DoLuaShared': self.do_shared,
            'DoLuaLevel': lambda name: self.do_file(name, LEVEL_DIRS),
            'Error': lambda *a: g.log(f'lua error {self.script} {u.name}: {a}'),
            'FNVHash': lambda s: fnv1a(s or ''),
            # the unit
            'GetThis': lambda: u,
            'GetOwner': lambda x=None: getattr(x or u, 'owner', None),
            'GetGoldRedirectTarget': lambda x=None: None,
            'GetHP': lambda x=None: (x or u).hp,
            'GetMaxHP': lambda x=None: (x or u).max_hp,
            'SetHP': self.set_hp,
            'IsDead': lambda x=None: not (x or u).alive,
            'GetMyPos': lambda: Point(u.pos[0], g.pk.y(u.pos), u.pos[1]),
            'GetPos': lambda x: Point(x.pos[0], g.pk.y(x.pos), x.pos[1]) if x is not None else None,
            'Make3DPoint': lambda x, y, z: Point(x, y, z),
            'SetGhosted': lambda on: setattr(u, 'ghosted', bool(on)),
            'GetCharVar': lambda name: self.vars.get(name, 0),
            'SetCharVar': lambda name, v: self.vars.__setitem__(name, v),
            'HasUnitTag': self.has_tag,
            # states
            'GetState': lambda: self.state,
            'SetState': self.set_state,
            'NetSetState': lambda s: None,
            'GetRoamState': lambda: self.roam,
            'SetRoamState': self.set_roam,
            'GetOriginalState': lambda: self.original_roam,
            # timers
            'InitTimer': self.init_timer,
            'StartTimer': lambda n: self.start_timer(n, reset=False),
            'ResetAndStartTimer': lambda n: self.start_timer(n, reset=True),
            'ResetTimer': lambda n: self.start_timer(n, reset=True, start=False),
            'StopTimer': self.stop_timer,
            'SetTimerDelay': self.set_delay,
            # leash
            'SetMyLeashedPos': lambda: setattr(self, 'leash_pos', Point(u.pos[0], g.pk.y(u.pos), u.pos[1])),
            'GetMyLeashedPos': lambda: self.leash_pos,
            'SetMyLeashedOrientation': lambda: None,
            'SetLeashOrientation': lambda: None,
            'GetLeashCounter': lambda: self.leash_counter,
            'SetLeashCounter': lambda n: setattr(self, 'leash_counter', n),
            'GetDistToRetreat': lambda: self.walk_dist(u.pos, self.leash_pos.pos),
            'GetWalkDistToLeashedPos': lambda: self.walk_dist(u.pos, self.leash_pos.pos),
            'SetStateAndMoveToLeashedPos': self.move_home,
            'IsMovementStopped': lambda: not u.path,
            # distances
            'DistanceBetweenObjectCenterAndPoint': lambda o, p: dist(self.pos_of(o), self.pos_of(p)),
            'WalkDistanceBetweenObjectCenterAndPoint': lambda o, p: self.walk_dist(self.pos_of(o), self.pos_of(p)),
            # targets
            'GetTarget': lambda: self.target,
            'SetStateAndCloseToTarget': self.close_to_target,
            'TurnOnAutoAttack': self.attack_on,
            'TurnOffAutoAttack': self.attack_off,
            'TargetInAttackRange': lambda: self.target is not None and u.in_reach(self.target),
            'TargetInCancelAttackRange': lambda: self.target is not None and u.in_reach(self.target, CANCEL_SLACK),
            'FindTargetWithFilter': lambda r, inc=None, exc=None: self.find(u.pos, r, inc, exc),
            'FindTargetNearPositionWithFilter': lambda p, r, inc=None, exc=None: self.find(self.pos_of(p), r, inc, exc),
            'IsValidEnemyWithFilter': lambda o, inc=None, exc=None: self.valid(o, inc, exc),
            # buffs the script gives itself (the frustration stacks)
            'AIScriptSpellBuffStackingAdd': self.buff_add,
            'AIScriptSpellBuffRemove': self.buff_remove,
        }
        for name, fn in fns.items():
            vm.register(name, fn)

    def do_file(self, name, dirs):
        if name in self.loaded:
            return
        self.loaded.add(name)
        p = script_path(name, dirs)
        if p is None:
            self.missing['script ' + name] = self.missing.get('script ' + name, 0) + 1
            return
        self.vm.load_file(p)

    def do_shared(self, name):
        self.do_file(name, SHARED_DIRS)

    # ------------------------------------------------------------------ helpers
    def pos_of(self, o):
        if isinstance(o, Point):
            return o.pos
        if isinstance(o, (tuple, list)):
            return (o[0], o[-1])
        return o.pos if o is not None else self.u.pos

    def walk_dist(self, a, b):
        g = self.g
        if g.nav.line_clear(a, b):
            return dist(a, b)
        pts = g.nav.path(a, b)
        if not pts:
            return dist(a, b)
        return sum(dist(p, q) for p, q in zip(pts, pts[1:]))

    def has_tag(self, o, tags):
        if o is None:
            return False
        want = {self.tag_names.get(t, t) for t in (tags.values() if isinstance(tags, dict) else tags or [])}
        return bool(unit_tags(o) & want)

    def valid(self, o, inc=None, exc=None):
        u = self.u
        if o is None or not getattr(o, 'alive', False) or not getattr(o, 'targetable', False) or o is u:
            return False
        if getattr(o, 'team', None) == u.team or getattr(o, 'kind', '') == 'plant':
            return False
        if inc and not self.has_tag(o, inc):
            return False
        if exc and self.has_tag(o, exc):
            return False
        return True

    def find(self, center, r, inc, exc):
        best = None
        for o in self.g.units.values():
            if self.valid(o, inc, exc):
                d = dist(o.pos, center)
                if d <= r + o.radius and (best is None or d < best[0]):
                    best = (d, o)
        return best[1] if best else None

    def set_hp(self, hp):
        u = self.u
        before = u.hp
        u.set_hp(min(u.max_hp, max(0.0, float(hp))))

    # ------------------------------------------------------------------ orders
    def set_roam(self, s):
        old, self.roam = self.roam, s
        if old != s and getattr(self, 'on_roam', None):
            self.on_roam(old, s)

    def set_state(self, s):
        old, self.state = self.state, s
        if old != s and getattr(self, 'on_state', None):
            self.on_state(old, s)

    def close_to_target(self, s, tgt):
        self.set_state(s)
        self.set_target(tgt)
        if tgt is not None and not self.u.in_reach(tgt):
            self.walk(tgt.pos)

    def set_target(self, tgt):
        old = self.target
        self.target = tgt
        if tgt is not old:
            for fn in self.g.ai_target_hooks if hasattr(self.g, 'ai_target_hooks') else ():
                fn(self.u, old, tgt)

    def attack_on(self, tgt=None):
        if tgt is not None:
            self.set_target(tgt)
        self.auto_attack = True
        if self.target is not None:
            self.u.target = self.target.net

    def attack_off(self, reason=None):
        self.auto_attack = False
        if reason == CONSTANTS['STOPREASON_MOVING'] and self.target is not None and self.state == CONSTANTS['AI_ATTACK']:
            return                               # it stops to walk after its target: the engine's chase (attack_tick)
        self.u.cancel_attack()
        self.u.target = None

    def move_home(self, s):
        self.set_state(s)
        self.set_target(None)
        self.auto_attack = False
        self.u.target = None
        self.walk(self.leash_pos.pos)

    # ------------------------------------------------------------------ timers
    def init_timer(self, name, delay, repeat=True):
        self.timers[name] = [float(delay), bool(repeat), True, self.g.t + float(delay)]

    def start_timer(self, name, reset=False, start=True):
        tm = self.timers.get(name)
        if tm is None:
            return
        if reset or not tm[2]:
            tm[3] = self.g.t + tm[0]
        if start:
            tm[2] = True

    def stop_timer(self, name):
        tm = self.timers.get(name)
        if tm is not None:
            tm[2] = False

    def set_delay(self, name, delay):
        tm = self.timers.get(name)
        if tm is not None:
            tm[0] = float(delay)

    # ------------------------------------------------------------------ buffs
    def buff_add(self, target, caster, name, stacks=1, max_stacks=1, duration=25000.0):
        g, sp = self.g, self.g.spells
        target = target or self.u
        if sp is None:
            return
        if not hasattr(target, 'buff_list'):
            target.buff_list = {}
        key = ('lua', name)
        b = target.buff_list.get(key)
        h = P.elf(name)
        if b is None:
            slot = sp.buff_slot(target)
            count = min(int(max_stacks or stacks), int(stacks))
            target.buff_list[key] = {'slot': slot, 'until': g.t + duration, 'hash': h, 'undo': None, 'known': True,
                                     'args': (target.net, slot, 1, h, 0), 'count': count}
            g.q += g.pk.buff_add(target.net, (caster or self.u).net, slot, 1, h, duration, count=count)
        else:
            b['count'] = min(int(max_stacks or 1e9), b.get('count', 1) + int(stacks))
            g.q += g.pk.buff_count(target.net, b['slot'], (caster or self.u).net, duration, b['count'])

    def buff_remove(self, target, name):
        target = target or self.u
        b = getattr(target, 'buff_list', {}).pop(('lua', name), None)
        if b is not None:
            self.g.q += self.g.pk.buff_remove(target.net, b['slot'], b['hash'])


FUNCTIONS = set()


def _collect():
    """the names this file supplies (for tools/lua_api_census.py)"""
    import inspect
    src = inspect.getsource(AIHost._install)
    import re
    FUNCTIONS.update(re.findall(r"'([A-Z]\w+)': ", src))


_collect()
