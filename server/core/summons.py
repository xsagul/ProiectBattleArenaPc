"""Units the champions' abilities create: traps, pets, clones, markers (a dagger on the ground), wards.

The real server's form [m: the live recording - wards, Lissandra's frozen thrall, the jungle companion; the
replays - Katarina's daggers (HiddenMinion / TestCubeRender), Shaco's boxes ...]: one packet 626 (S2C spawn of a
minion-like unit) inside a 239 container, with 684 (health, place) beside it, then the unit's replicated values;
afterwards the unit lives as any other: animations, buffs, its attacks, its death (1112) and removal.
626: +0x10 net id, +0x18 owner (the champion), +0x1c place (vec3), +0x38 its name, +0x4c a second place, +0x5c,
+0x60, +0x64 the team (1 order, 2 chaos), +0x68 the game time, +0x70 the character (whose record and model),
+0x81 a ward, +0x84, +0x8e.

Which unit a spell creates, where and with which flags is read from the spell's template (templates.py); what the
unit does is its record's (gamedata: the character's bin in the champion's wad) and its kind:
  trap      record tagged Special_Trap: stands, hidden from enemies after the arm time, goes off when an enemy
            champion steps near (the template's 'spawn_other' events: what it does to them)
  marker    HiddenMinion / TestCube*: not a body, a place the spell remembers (daggers, zones): untargetable
  pet       anything else: attacks enemies near its owner, follows the owner
"""
import math
import struct

from . import gamedata as G
from . import packets as P
from .units import Unit, dist, ORDER, CHAOS

MARKERS = ('hiddenminion', 'testcube')
TRAP_RANGE = 135.0                # [a] how near an enemy champion must come to set a trap off
_records = {}


def record(owner_champion, character):
    """the character's record numbers (its bin in the owner champion's wad, else the map's)"""
    key = (owner_champion, character)
    if key not in _records:
        import bin_tree as BT
        import os
        st = None
        for wad in (os.path.join(G.GAME, 'Champions', f'{owner_champion}.wad.client'), G.MAP_WAD):
            try:
                ents = BT.entries(wad, f'data/characters/{character.lower()}/{character.lower()}.bin')
            except Exception:
                ents = []
            rec = G._root_record(ents, character) if ents else None
            if rec is not None:
                st = G.record_stats(rec)
                # its basic attack's missile (ShacoBoxBasicAttack 1500): the spell lives in the owner's bin
                ba = (rec.get('basicAttack') or {})
                atk = G.first_name(ba.get('mAttackName')) or f'{character}BasicAttack'
                try:
                    sd = G.champion(owner_champion).spell_data(atk) if wad != G.MAP_WAD else {}
                except Exception:
                    sd = {}
                st['missile_speed'] = float(sd.get('missileSpeed', 0.0) or 0.0)
                break
        _records[key] = st or {'name': character, 'hp': 100.0, 'ad': 0.0, 'armor': 0.0, 'mr': 0.0, 'speed': 0.0,
                                'range': 0.0, 'as': 0.625, 'radius': 30.0, 'sight': 0.0, 'tags': []}
    return _records[key]


class Summon(Unit):
    kind = 'summon'
    repl_cls = 'lane_minion'

    def __init__(self, game, net, owner, name, character, pos, base, values626):
        super().__init__(game, net, owner.team, character, pos, base)
        self.owner, self.label, self.character = owner, name, character
        self.values626 = values626
        tags = [t.lower() for t in base.get('tags', [])]
        low = (name + ' ' + character).lower()
        self.marker = any(m in low for m in MARKERS)
        self.trap = 'special_trap' in tags
        self.targetable = not self.marker
        self.can_move = base.get('speed', 0.0) > 0 and not self.trap and not self.marker
        self.born = game.t
        self.expires = None
        self.spawn_body = None            # the 626 an enemy is given with its first sight of it
        self.next_think = 0.0
        self.armed_at = None

    def replicate_stats(self):
        self.set_many({'mMaxHP': self.max_hp, 'mBaseAttackDamage': self.base_ad, 'mArmor': self.armor,
                       'mAttackRange': self.range, 'mMoveSpeed': self.speed})


class Summons:
    def __init__(self, game):
        self.g = game
        self.units = []

    def spawn(self, owner, values, place=None, life=None, pid=626):
        """a unit as the template's 626 (a minion-like unit) or 1038 (a pet / a clone: Shaco's R, Tibbers) describes
        it -> the Summon (its packets queued)"""
        g, pk = self.g, self.g.pk
        if pid == 1038:
            return self.spawn_pet(owner, values, place, life)
        name = _text(values.get('+0x38')) or 'HiddenMinion'
        character = _text(values.get('+0x70')) or name
        base = dict(record(owner.name, character))
        pos = place or owner.pos
        net = g.new_net()
        u = Summon(g, net, owner, name, character, pos, base, values)
        g.add(u)
        self.units.append(u)
        if life:
            u.expires = g.t + life
        v = dict(values)
        team = 1 if owner.team == ORDER else 2
        y = pk.y(pos)
        v.update({'+0x10': P.u32(net), '+0x18': P.u32(owner.net), '+0x1c': P.vec3(pos[0], y, pos[1]),
                  '+0x4c': P.vec3(pos[0], y, pos[1] + 1.0), '+0x64': f'{team:02x}', '+0x68': P.f32(g.t)})
        body = pk.enc(626, v)
        u.spawn_body = body
        u.dirty = self.values(u)
        if g.vision is not None and u.team != g.vision.team:
            pass                                         # the vision brings it with its first sight (vision.enter)
        else:
            import forms16
            g.q.append((1, forms16.CONTAINER, net, pk.enc(forms16.CONTAINER, forms16.pack([(626, net, body)]))))
            g.q += pk.enter(g.t, net, u.hp, u.max_hp, u.pos, u.facing, None, u.speed)[1:]
        g.stat_outputs(u, zero_first=True)
        return u

    def spawn_pet(self, owner, values, place, life=None):
        """1038 [m: Shaco's clone in the replays]: +0x10 the character ('Shaco'), +0x24 its place, +0x40 a time,
        +0x48 the owner, +0x50 its duration (25000 = until killed), +0x58 its name ('Hallucinate'), +0x70 the AI
        script ('AnnieTibbersPet.lua' for Shaco's clone too); then 684 and its values, as any unit coming into sight"""
        g, pk = self.g, self.g.pk
        character = _text(values.get('+0x10')) or owner.name
        base = dict(record(owner.name, character))
        pos = place or owner.pos
        net = g.new_net()
        u = Summon(g, net, owner, _text(values.get('+0x58')) or character, character, pos, base, values)
        u.marker, u.trap, u.targetable = False, False, True
        u.can_move = True
        g.add(u)
        self.units.append(u)
        dur = struct.unpack('<f', bytes.fromhex(values['+0x50']))[0] if isinstance(values.get('+0x50'), str) else 0.0
        if life or 0 < dur < 1000:
            u.expires = g.t + (life or dur)
        v = dict(values)
        v.update({'+0x24': P.vec3(pos[0], pk.y(pos), pos[1]), '+0x48': P.u32(owner.net), '+0x40': P.f32(g.t)})
        body = pk.enc(1038, v)
        u.spawn_body, u.spawn_pid = body, 1038
        u.dirty = self.values(u)
        if g.vision is None or u.team == g.vision.team:
            g.q.append((1, 1038, net, body))
            g.q += pk.enter(g.t, net, u.hp, u.max_hp, u.pos, u.facing, None, u.speed)
        return u

    def values(self, u):
        """[m: the ward's and the thrall's first replication] the values a new unit is given"""
        return {'mLifetime': 0.0, 'mMaxLifetime': 0.0, 'mLifetimeTicks': 0.0, 'mPAR': 0.0, 'mMaxPAR': 0.0,
                'ActionState': 16781327, 'ActionState2': 4, 'StatusFlags': 1, 'mBaseAttackDamage': u.base_ad,
                'mArmor': u.armor, 'mSpellBlock': u.mr, 'mAttackSpeedMod': 1.0, 'mHP': u.hp, 'mMaxHP': u.max_hp,
                'mAttackRange': u.range, 'mCritDamageMultiplier': 1.75, 'mMoveSpeed': u.speed, 'mScaleSkinCoef': 1.0,
                'mIsTargetable': 1 if u.targetable else 0, 'mIsTargetableToTeamFlags': 4 if u.targetable else 3,
                'mPAREnabled': 1, 'mSAREnabled': 1, 'mPercentMultiplicativeAttackSpeedMod': 1.0}

    def remove(self, u, killer=None, after=4.0):
        """the unit dies (1112) and is taken away (1090) `after` seconds later [m: the ward's 4 s, as a minion's]
        - None: the template says when (its own 1090)"""
        if u in self.units:
            self.units.remove(u)
        if u.alive:
            u.alive = False
            g = self.g
            g.q += g.pk.death(u, killer.net if killer is not None else 0)
            if after is not None:
                g.at(g.t + after, lambda t2, u=u: g.remove(u) if u.net in g.units else None)

    # ------------------------------------------------------------------ the frame
    def tick(self, t, dt):
        g = self.g
        for u in list(self.units):
            if not u.alive:
                self.units.remove(u)
                continue
            if u.expires is not None and t >= u.expires:
                self.remove(u)
                continue
            if u.marker:
                continue
            if u.path:
                u.advance(dt)
            state = u.attack_tick(t) if u.range > 0 and u.base_ad > 0 else 'idle'
            if state == 'windup' or t < u.next_think:
                continue
            u.next_think = t + 0.25
            if u.trap and (u.armed_at is None or t < u.armed_at):
                continue
            tgt = g.units.get(u.target) if u.target else None
            if tgt is None or not u.can_target(tgt):
                near = [(d, o) for d, o in g.enemies_near(u, max(u.range, 300.0) + 100.0) if g.seen_by(u.team, o)]
                if u.trap:
                    # [a] any enemy unit sets it off (Shaco's boxes fear minions: their data has MinionFearDuration);
                    # a trap whose owner's champions-only tag says so: champions only
                    heroes_only = getattr(u, 'heroes_only', False)
                    near = [(d, o) for d, o in near if not o.is_structure and (o.is_hero or not heroes_only)
                            and d <= getattr(u, 'trigger_range', TRAP_RANGE) + o.radius]
                    if near and getattr(u, 'on_trigger', None):
                        u.on_trigger(u, [o for d, o in near])
                        continue
                own = g.units.get(u.owner.target) if u.owner.target else None
                if own is not None and u.can_target(own) and dist(own.pos, u.pos) <= u.range + 300.0:
                    u.target = own.net
                elif near:
                    u.target = min(near, key=lambda x: x[0])[1].net
            if u.can_move and not u.target and dist(u.pos, u.owner.pos) > 250.0:
                u.path_to(u.owner.pos)
            elif u.can_move and u.target:
                tgt = g.units.get(u.target)
                if tgt is not None and not u.in_reach(tgt) and not u.path:
                    u.path_to(tgt.pos)


def _text(v):
    try:
        return bytes.fromhex(v['text']).decode('latin-1').rstrip('\0') if isinstance(v, dict) else ''
    except Exception:
        return ''


def setup(game, session=None):
    game.summons = Summons(game)
    game.systems.append(game.summons.tick)
