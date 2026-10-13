"""Spells of every champion from the game's own data - one generic system, no per-champion code.

What the data says about a spell (the champion's bin, gamedata.Champion):
  SpellDataResource   targeting (mTargetingTypeData), castRange, castRadius, mLineWidth, castConeAngle, missile
                      (mMissileSpec / missileSpeed), cast times (mCastTime | spellCastTime + spellTotalTime, else the
                      0.5 / 2.0 defaults), cooldownTime and mana per rank, mSpellTags (Trait_Ranged_StopsFirstHit,
                      Trait_Ranged_Piercing, Trait_AoE, Trait_DoT, PositiveEffect_Teleport,
                      Trait_PlayerSelectedDashDirection, PositiveEffect_EmpowerAttack, Trait_AttackReset ...)
  BotData             Riot's own description of the spell for its bots: DamageTag = the damage type (0 physical,
                      1 magic, 2 true), the damage calculation (a key into mSpellCalculations), and a list of effects
                      {EffectTag, EffectCalculation}:   [meanings read from known spells, see docs]
                          1 move speed change (negative = slow)      16 heal            128 dash / blink
                          256 dash speed          2048 cannot attack        4096 cannot move
                          16384 cannot cast       (2048 + 4096 + 16384 with one duration = a stun)
                          32768 the missile's width     4194300 knocked back (distance)     16777200 knocked up
What the live server sends for a cast [measured]: 1215 (the cast struct; the client plays the cast's animation and
shows the cooldown from it), 938 + 743 when the cast's own missile leaves, 223 + 938 + 743 for a missile that is a
spell of its own, 433 / 118 when a missile hits / ends, 435 / 262 for buffs, 1140 for a dash, a teleport entry in
61 for a blink, 150 for damage.
What is ours [a]: whom an area hits and when, how long a slow lasts when the data does not say, the dash's speed
when the data gives none, the tick rate of damage over time.
"""
import json
import math
import os

from . import gamedata as G
from . import packets as P
from .units import dist

import spell_calc as SC

# [the replays: Alistar Q / Cho'Gath Q knock-up 30, Alistar W knockback 31, Cho'Gath W silence 7] LoL's BuffType numbers
STUN, SILENCE, SLOW, SNARE, HASTE, KNOCKUP, DISARM, DAMAGE, ENHANCER = 5, 7, 11, 12, 15, 30, 32, 13, 2
T_SLOW, T_HEAL, T_DASH, T_DASH_SPEED, T_DISARM, T_ROOT, T_SILENCE, T_WIDTH = 1, 16, 128, 256, 2048, 4096, 16384, 32768
T_KNOCKBACK, T_KNOCKUP = 4194300, 16777200
ACTION_NORMAL = 16777231          # [m] a champion free to act; bits 0 / 1 / 2 = can attack / cast / move
# LoL's buff types [m: 5 stun, 7 silence, 11 slow, 12 snare live; the others by the enum's order]
CC_TYPES = {5: 'stun', 7: 'silence', 8: 'taunt', 11: 'slow', 12: 'snare', 22: 'fear', 23: 'charm', 25: 'suppress',
            29: 'flee', 30: 'knockup', 31: 'knockback', 32: 'disarm', 35: 'asleep'}
DEFAULT_SLOW_TIME, DEFAULT_DASH_SPEED, AREA_DELAY = 2.0, 1200.0, 0.25
SELF_TYPES = ('Self', 'SelfAoe')
LINE_TYPES = ('direction', 'DragDirection', 'WallDetection')
PLACE_TYPES = ('Location', 'LocationClamped', 'Area', 'AreaClamped', 'TerrainLocation', 'TerrainType')
_infos = {}


def _at(lst, rank, default=0.0):
    if isinstance(lst, list) and lst:
        return float(lst[min(rank, len(lst) - 1)])
    if isinstance(lst, (int, float)):
        return float(lst)
    return default


class Info:
    """one spell as the simulation uses it"""
    def __init__(self, champ, name):
        o = champ.spell(name) or {}
        sd = o.get('mSpell') or {}
        self.champ, self.name, self.obj, self.sd = champ, name, o, sd
        self.tags = set(sd.get('mSpellTags') or [])
        tt = sd.get('mTargetingTypeData')
        self.targeting = tt if isinstance(tt, str) else (tt.get('_type') if isinstance(tt, dict) else None) or 'Target'
        mv = (sd.get('mMissileSpec') or {}).get('movementComponent') or {}
        self.missile_speed = float(sd.get('missileSpeed', 0) or 0) or float(mv.get('mSpeed', 0) or 0)
        self.own_missile = 'mMissileSpec' in sd
        self.width = float(sd.get('mLineWidth', 0) or 0) or float((sd.get('mMissileSpec') or {}).get('mMissileWidth', 0) or 0)
        self.cone = float(sd.get('castConeAngle', 0) or 0)
        if 'mCastTime' in sd:
            self.cast_time = float(sd['mCastTime'])
            self.total_time = max(self.cast_time, float(sd.get('spellTotalTime', 0) or 0))
        elif sd.get('spellCastTime') or sd.get('spellTotalTime'):
            self.cast_time, self.total_time = float(sd.get('spellCastTime', 0) or 0), float(sd.get('spellTotalTime', 0) or 0)
        else:
            self.cast_time = 0.5 * (1.0 + float(sd.get('delayCastOffsetPercent', 0) or 0))
            self.total_time = max(self.cast_time, 2.0 * (1.0 + float(sd.get('delayTotalTimePercent', 0) or 0)))
        self.scripted = bool(int(sd.get('flags', 0) or 0) & 4)
        bot = o.get('BotData') or {}
        self.dmg_type = bot.get('DamageTag')
        self.dmg_calc = bot.get('{6d548702}')
        self.effects = [(e.get('EffectTag'), e.get('EffectCalculation')) for e in (bot.get('{ec17e271}') or []) if isinstance(e, dict)]
        tags = {t for t, c in self.effects}
        self.blink = 'PositiveEffect_Teleport' in self.tags and T_DASH in tags
        self.dash = not self.blink and (T_DASH in tags or 'Trait_PlayerSelectedDashDirection' in self.tags)
        self.stops_first = 'Trait_Ranged_StopsFirstHit' in self.tags or (
            self.own_missile and any(b.get('_type') == 'DestroyOnHit' for b in (sd.get('mMissileSpec') or {}).get('behaviors', []) if isinstance(b, dict)))
        self.aoe = 'Trait_AoE' in self.tags
        self.dot = 'Trait_DoT' in self.tags
        self.empower = 'PositiveEffect_EmpowerAttack' in self.tags or ('Trait_AttackReset' in self.tags and self.targeting in SELF_TYPES)
        self.missile_name = None
        if not self.own_missile and self.targeting not in SELF_TYPES:
            self.missile_name = self._missile_spell()
            if self.missile_name:
                msd = (champ.spell(self.missile_name) or {}).get('mSpell') or {}
                mmv = (msd.get('mMissileSpec') or {}).get('movementComponent') or {}
                self.missile_speed = float(mmv.get('mSpeed', 0) or 0) or float(msd.get('missileSpeed', 0) or 0) or self.missile_speed
                self.width = self.width or float((msd.get('mMissileSpec') or {}).get('mMissileWidth', 0) or 0)
                if any(b.get('_type') == 'DestroyOnHit' for b in (msd.get('mMissileSpec') or {}).get('behaviors', []) if isinstance(b, dict)):
                    self.stops_first = True

    def _missile_spell(self):
        """a spell of the champion named after this one that carries a missile (RocketGrab -> RocketGrabMissile)"""
        low = self.name.lower()
        cand = [n for n, v in self.champ.objects.items() if n != self.name and n.lower().startswith(low)
                and 'mMissileSpec' in (v.get('mSpell') or {})]
        for suffix in ('missile', 'mis', 'missile1', 'mis1', 'spell', 'attack'):
            for n in cand:
                if n.lower() == low + suffix:
                    return n
        cand = [n for n in cand if not any(w in n.lower() for w in ('return', 'vis', 'dummy', 'ammo', 'self'))]
        return min(cand, key=lambda n: (len(n), n)) if cand else None

    def range(self, rank):
        sd = self.sd
        r = _at(sd.get('castRange'), rank)
        shown = _at(sd.get('castRangeDisplayOverride'), rank)
        if self.targeting in PLACE_TYPES + LINE_TYPES + ('Cone',) and shown and (r > 5000 or r <= 0):
            return shown
        return r if 0 < r < 5000 else (shown or 600.0)

    def radius(self, rank):
        r = _at(self.sd.get('castRadius'), rank)
        if self.targeting in SELF_TYPES:
            r = max(r, _at(self.sd.get('castRangeDisplayOverride'), rank))     # Garen E: radius 35, shown 325
            if r < 50.0:
                # [data: Mundo's W, Samira's W ...] a spell around its caster with no radius: its cast range is it
                rr = _at(self.sd.get('castRange'), rank)
                if 50.0 < rr <= 1000.0:
                    return rr
        return r

    def wiki(self):
        """the wiki's record of this spell when it is one of the champion's four (gamedata.wiki)"""
        if not hasattr(self, '_wiki'):
            sp = list(self.champ.spells[:4])
            self._wiki = G.wiki(self.champ.name, 'QWER'[sp.index(self.name)]) if self.name in sp else None
        return self._wiki

    def cooldown(self, rank):
        # [m: the real casts' cooldowns (1215 +0x80) of the 16 spells whose two differ - Kai'Sa W 20, Syndra W 13,
        # Mordekaiser R 120 ...] the Cooldown block's values are the server's; cooldownTime is an older copy
        cd = _at((self.sd.get('Cooldown') or {}).get('values'), rank) or _at(self.sd.get('cooldownTime'), rank)
        if cd <= 0:
            # [data: Lux's Q, Rakan's E ...: no cooldownTime (kept by ammo / a script)] the wiki's
            w = self.wiki()
            if w and w.get('cooldown'):
                return float(w['cooldown'][min(max(rank, 1), len(w['cooldown'])) - 1])
        return cd

    def wiki_damage(self, hero, rank):
        """(amount, type) by the wiki's numbers for this spell (base by rank + its AP / AD ratios); None when the wiki
        has none or a ratio is of something else (the target's health ...)"""
        w = self.wiki()
        dm = (w or {}).get('damage')
        if not dm or not dm.get('base'):
            return None
        v = dm['base'][min(max(rank, 1), len(dm['base'])) - 1]
        for vals, of in dm.get('ratios') or []:
            if not vals:
                continue
            pct = vals[min(max(rank, 1), len(vals)) - 1] / 100.0
            o = of.lower()
            if o == 'ap':
                v += pct * hero.ap
            elif o == 'bonus ad':
                v += pct * hero.bonus['ad']
            elif o == 'ad':
                v += pct * (hero.base_ad + hero.bonus['ad'])
            else:
                return None
        return float(v), dm.get('type', 1)

    def wiki_cc(self, kind, rank):
        """seconds (or the slow's share) the wiki gives for this kind of crowd control at a rank; None: not said"""
        cc = (self.wiki() or {}).get('cc') or {}
        names = {'stun': ('stun', 'disable'), 'snare': ('root',), 'root': ('root',), 'knockup': ('knockup',),
                 'silence': ('silence',), 'charm': ('charm', 'disable'), 'fear': ('fear', 'disable'), 'flee': ('fear',),
                 'taunt': ('taunt', 'disable'), 'asleep': ('sleep',), 'suppress': ('suppress',),
                 'slow': ('slow',), 'slow_time': ('slow_time',)}.get(kind, (kind,))
        for n in names:
            vals = cc.get(n)
            if vals:
                return float(vals[min(max(rank, 1), len(vals)) - 1])
        return None

    def mana(self, rank):
        return _at(self.sd.get('mana'), rank - 1) if self.sd.get('mana') else 0.0

    def calc(self, calc, hero, rank):
        if not isinstance(calc, dict):
            return None
        sp = {'mSpell': dict(self.sd)}
        sp['mSpell']['mSpellCalculations'] = dict(self.sd.get('mSpellCalculations') or {}, **{'{c}': calc})
        st = SC.Stats(ad=(hero.base_ad, hero.bonus['ad']), ap=(0.0, hero.ap), armor=(hero.base_armor, hero.bonus['armor']),
                      mr=(hero.base_mr, hero.bonus['mr']), hp=(hero.max_hp - hero.bonus['hp'], hero.bonus['hp']),
                      ms=(hero.speed, 0.0), mana=(hero.max_par, 0.0), crit=(hero.crit, 0.0))
        st.v['as'] = (hero.attack_speed, 0.0)
        try:
            return float(SC.evaluate(sp, '{c}', rank, hero.level, st))
        except Exception:
            return None

    def damage(self, hero, rank):
        """(amount, type) from the spell's own bot data; else the calculation named like a damage"""
        v = self.calc(self.dmg_calc, hero, rank)
        if (v is None or v <= 0) and isinstance(self.dmg_calc, dict):
            # [data: Alistar's Q ...] the bot data's calculation is only a pointer to one of the spell's own
            # (mMultiplier {calculation by key}, no parts of its own)
            key = (self.dmg_calc.get('mMultiplier') or {}).get('mSpellCalculationKey')
            if key and key in (self.sd.get('mSpellCalculations') or {}):
                v = self.calc(self.sd['mSpellCalculations'][key], hero, rank)
        if v is None or v <= 0:
            named = SC.named_calcs({'mSpell': self.sd}) if self.sd.get('mSpellCalculations') else {}
            key = next((named[w] for w in ('TotalDamage', 'Damage', 'TotalDamageTooltip') if w in named), None) or \
                next((k for n, k in named.items() if 'damage' in n.lower() and 'bonus' not in n.lower()), None)
            if key:
                v = self.calc(self.sd['mSpellCalculations'][key], hero, rank)
        if v is None or v <= 0:
            return 0.0, P.MAGIC
        dtype = self.dmg_type if self.dmg_type in (0, 1, 2) else P.MAGIC
        return v, dtype

    def named_control(self, rank):
        """a spell without bot data (213 of the 692 Q / W / E / R): what it does to whom it hits, read from the names
        of its data values (54 of them have such: StunDuration, SlowAmount + SlowDuration, RootDuration ...) ->
        {'stun' | 'root' | 'silence' | 'knockup': seconds, 'slow': (share, seconds)}"""
        out = {}
        slow, slow_time = None, None
        for dv in self.sd.get('DataValues') or self.sd.get('mDataValues') or []:
            if not isinstance(dv, dict):
                continue
            name = str(dv.get('name') or dv.get('mName') or '').lower()
            if name.startswith(('tooltip', 'self')) or 'immun' in name or 'range' in name or 'radius' in name or 'damage' in name:
                continue
            v = _at(dv.get('values') or dv.get('mValues'), rank)
            if not v or v < 0:
                continue
            if name.endswith('duration') or name.endswith('time'):
                for word, kind in (('stun', 'stun'), ('fear', 'stun'), ('charm', 'stun'), ('taunt', 'stun'), ('sleep', 'stun'),
                                   ('suppress', 'stun'), ('knockup', 'knockup'), ('root', 'root'), ('snare', 'root'),
                                   ('silence', 'silence')):
                    if word in name and v <= 5.0:
                        out[kind] = max(out.get(kind, 0.0), v)
                if 'slow' in name and v <= 6.0:
                    slow_time = v
            elif 'slow' in name and ('amount' in name or 'percent' in name or name == 'slow' or 'potency' in name):
                slow = v / 100.0 if v > 1.0 else v
        if slow and 0.0 < slow < 1.0:
            out['slow'] = (slow, slow_time or DEFAULT_SLOW_TIME)
        return out

    def data_value(self, names, rank):
        for dv in self.sd.get('DataValues') or self.sd.get('mDataValues') or []:
            if isinstance(dv, dict) and (dv.get('name') or dv.get('mName')) in names:
                return _at(dv.get('values') or dv.get('mValues'), rank)
        return None


def info(champ, name):
    key = (champ.name, name)
    if key not in _infos:
        _infos[key] = Info(champ, name)
    return _infos[key]


def mspec(sd):
    """a spell's missile as its data describes it (mMissileSpec) [data: movementComponent FixedSpeedMovement {mSpeed} |
    AcceleratingMovement {mInitialSpeed, mAcceleration, mMinSpeed, mMaxSpeed}, mTracksTarget, mProjectTargetToCastRange
    (it flies the whole cast range, not to the aimed place); behaviors CastOnHit (it hits what it meets), DestroyOnHit
    (the first one stops it), CastOnMovementComplete (its effect is where it ends)]"""
    ms = (sd or {}).get('mMissileSpec') or {}
    mv = ms.get('movementComponent') or {}
    beh = {b.get('_type') for b in ms.get('behaviors') or [] if isinstance(b, dict)}
    speed = float(mv.get('mInitialSpeed', 0) or 0) or float(mv.get('mSpeed', 0) or 0) or float((sd or {}).get('missileSpeed', 0) or 0)
    return {'has': bool(ms), 'speed': speed, 'accel': float(mv.get('mAcceleration', 0) or 0),
            'vmin': float(mv.get('mMinSpeed', 0) or 0), 'vmax': float(mv.get('mMaxSpeed', 0) or 0),
            'width': float(ms.get('mMissileWidth', 0) or 0) or float((sd or {}).get('mLineWidth', 0) or 0),
            'project': bool(mv.get('mProjectTargetToCastRange')), 'tracks': bool(mv.get('mTracksTarget', 1)),
            'collide': 'CastOnHit' in beh, 'stops': 'DestroyOnHit' in beh, 'on_complete': 'CastOnMovementComplete' in beh,
            'range': _at((sd or {}).get('castRange'), 0), 'radius': _at((sd or {}).get('castRadius'), 0)}


class Missile:
    def __init__(self, net, owner, inf, rank, start, direction, speed, reach, target=None, width=60.0, accel=0.0, vmin=0.0,
                 vmax=0.0, stops=None, collide=True, returning=False, hit=None, on_end=None):
        self.net, self.owner, self.inf, self.rank = net, owner, inf, rank
        self.pos, self.dir, self.speed, self.left = start, direction, speed, reach
        self.target, self.width = target, width
        self.accel, self.vmin, self.vmax = accel, vmin, vmax
        self.stops = inf.stops_first if stops is None else stops
        self.collide, self.returning, self.on_end = collide, returning, on_end
        self.hit = set() if hit is None else hit       # the units it has hit (shared by the missiles of a fan)
        self.done = False


_buff_refresh = None


def buff_refresh():
    global _buff_refresh
    if _buff_refresh is None:
        try:
            _buff_refresh = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'buff_refresh16.json')))
        except Exception:
            _buff_refresh = {}
    return _buff_refresh


class Spells:
    def __init__(self, game):
        self.g = game
        self.missiles = []
        self.buffs = []                  # [until, unit, key]
        self.zones = []
        self.pending = {}                # hero net -> (slot, aim, target net): a cast waiting for the champion to be in range
        self.casts = 0
        self.dashes = []                 # [hero, dest, speed, on_land]

    # ------------------------------------------------------------------ requests
    def request(self, hero, r):
        """a cast request (the client's 707, a bot's choice) -> a line for the log"""
        slot = r['slot']
        aim = r['cursor'] if r.get('cursor') and r['cursor'] != (0.0, 0.0) else r.get('target_place') or hero.pos
        target = r.get('target') or 0
        if target == hero.net:
            target = 0
        if slot in (4, 5):
            return self.summoner(hero, slot, aim, target)
        if slot == 13:
            return self.recall(hero)
        if 6 <= slot <= 12 and r.get('hash'):
            return self.item_cast(hero, slot, r['hash'], aim, target)
        if not 0 <= slot <= 3:
            return f'cast slot {slot}: not handled yet'
        return self.cast(hero, slot, aim, target)

    def item_cast(self, hero, slot, name_hash, aim, target=0):
        """an item's or a trinket's active (slots 6 - 12) as the real server played it [the cast evidence: Item2003
        the potion, TrinketTotemLvl1 the ward, ZhonyasHourglass ...]: its 1215 with the real cast times, then its
        template (from this champion's evidence, else any champion's)"""
        g, tp = self.g, getattr(self.g, 'templates', None)
        found = tp.find_hash(hero.name, name_hash) if tp is not None else None
        if found is None or not hero.alive:
            return f'{hero.name} item slot {slot} {name_hash:08x}: no template'
        champ, key = found
        ct, tt = tp.cast_times(champ, key)
        ct, tt = max(0.0, ct or 0.0), max(0.0, tt or 0.0)
        tgt = g.units.get(target) if target else None
        here = hero.pos
        end = aim or here
        self.casts += 1
        cast_id, missile_id = g.new_net(), g.new_net()
        tpl = tp.of(champ, key) or {}
        package = int.from_bytes(bytes.fromhex(((tpl.get('cast') or {}).get('+0x18') or {}).get('+0xa0', '00000000')), 'little')             if isinstance(((tpl.get('cast') or {}).get('+0x18') or {}).get('+0xa0'), str) else 0
        d = math.hypot(end[0] - here[0], end[1] - here[1])
        direction = ((end[0] - here[0]) / d, (end[1] - here[1]) / d) if d > 1.0 else hero.facing
        g.q += g.pk.cast(g.t, hero.net, name_hash, slot, self.casts, cast_id, missile_id, end, end, here, direction,
                         ct, tt, 0.0, 0.0, tgt.net if tgt else 0, package=package, champion=hero.name)
        tp.play(hero, key, end, end, here, tgt, cast_id, missile_id, champ=champ)
        return f'{hero.name} uses {key} (slot {slot})'

    def can_cast(self, hero, slot):
        t = self.g.t
        if not hero.alive or slot >= len(hero.champ.spells):
            return 'dead or no spell'
        if hero.spell_levels[slot] <= 0:
            kits = getattr(self.g, 'kits', None)
            if kits is None or not kits.call(hero, 'learnt', hero, slot):
                return 'not learnt'
        if t < hero.cooldowns[slot]:
            return f'on cooldown {hero.cooldowns[slot] - t:.1f} s'
        if t < hero.cc_until or t < getattr(hero, 'silence_until', 0.0):
            return 'cannot cast now'
        if t < hero.casting_until:
            return 'casting'
        if hero.par < hero.mana_cost(slot) - 1e-6:
            return 'no mana'
        return None

    def cast(self, hero, slot, aim, target=0, queued=False):
        g = self.g
        kits = getattr(g, 'kits', None)
        if kits is not None:
            took = kits.call(hero, 'cast_request', hero, slot, aim, target)
            if took:
                return took                              # the kit took it (a recast that is no spell: Flash Frost's)
        why = self.can_cast(hero, slot)
        if why:
            return f'{hero.name} slot {slot}: {why}'
        inf = info(hero.champ, hero.spell_name(slot))
        rank = hero.spell_levels[slot]
        tgt = g.units.get(target) if target else None
        if inf.targeting == 'Target' and tgt is None:
            # a spell on a unit asked for with a place: the enemy nearest to that place
            near = [(dist(o.pos, aim), o) for o in g.units.values() if o.alive and o.targetable and o.team != hero.team
                    and not o.is_structure and o.kind != 'plant' and dist(o.pos, aim) <= 250.0]
            tgt = min(near, key=lambda x: x[0])[1] if near else None
            if tgt is None:
                return f'{hero.name} {inf.name}: needs a target'
        if tgt is not None and inf.targeting in ('Target', 'TargetOrLocation'):
            aim = tgt.pos
        # out of range: walk until in range, then cast (LoL's own behaviour for targeted and placed spells)
        rng = self.range_of(hero, inf, rank)
        need = None
        if inf.targeting == 'Target' or (inf.targeting == 'TargetOrLocation' and tgt is not None):
            need = rng + hero.radius + (tgt.radius if tgt else 0.0)
        elif inf.targeting in PLACE_TYPES and not inf.dash and not inf.blink and 'Clamped' not in inf.targeting and                 _at(inf.sd.get('castRange'), rank) < 5000:
            need = rng                                   # [data] a cast range of 25000 is global (Ashe's arrow)
            if inf.sd.get('mProjectTargetToCastRange'):
                need += 200.0                            # [wiki, Aurelion Sol E] cast at the edge if within 200 beyond it
        if need is not None and dist(hero.pos, aim) > need + 5.0:
            self.pending[hero.net] = (slot, aim, target)
            hero.order = ('cast', slot)
            hero.target = None
            hero.path_to(aim)
            return f'{hero.name} {inf.name}: walking into range ({dist(hero.pos, aim):.0f} > {need:.0f})'
        self.pending.pop(hero.net, None)
        self.begin(hero, slot, inf, rank, aim, tgt)
        return f'{hero.name} casts {inf.name} (rank {rank}, {inf.targeting}) at ({aim[0]:.0f}, {aim[1]:.0f})' + \
               (f' on {tgt.name}' if tgt else '')

    def range_of(self, hero, inf, rank):
        """the spell's cast range now: the data's, or its kit's (a range growing with level, another during a dash)"""
        kits = getattr(self.g, 'kits', None)
        r = kits.call(hero, 'cast_range', hero, inf, rank) if kits is not None else None
        return r if r else inf.range(rank)

    # ------------------------------------------------------------------ a cast begins
    def begin(self, hero, slot, inf, rank, aim, tgt):
        g, t = self.g, self.g.t
        here = hero.pos
        dx, dz = aim[0] - here[0], aim[1] - here[1]
        d = math.hypot(dx, dz)
        direction = (dx / d, dz / d) if d > 1.0 else hero.facing
        rng = self.range_of(hero, inf, rank)
        if inf.targeting in SELF_TYPES:
            aim = end = here
            direction = hero.facing
        elif inf.targeting in LINE_TYPES or inf.targeting == 'Cone' or (inf.targeting in PLACE_TYPES and inf.width > 0 and inf.missile_speed > 0 and not inf.aoe):
            tp0 = getattr(g, 'templates', None)
            reach = ((tp0.geom(hero.name, inf.name) if tp0 is not None else None) or {}).get('reach')
            if reach and reach['hi'] - reach['lo'] > 40.0 and reach['hi'] > 50.0 and inf.targeting != 'Cone':
                # [the replays] the real casts ended at different distances: where it was aimed, within its reach
                length = min(max(d, 1.0), reach['hi'])
            else:
                length = reach['med'] if reach and reach['med'] > 50.0 and reach['hi'] - reach['lo'] <= 40.0 else rng
            end = (here[0] + direction[0] * length, here[1] + direction[1] * length)
        elif inf.targeting in PLACE_TYPES:
            if d > rng > 0:
                aim = (here[0] + direction[0] * rng, here[1] + direction[1] * rng)
            end = aim
        else:
            end = aim
        if getattr(hero, 'stealth_until', 0.0) > t and inf.sd.get('mCastingBreaksStealth'):
            from .units import reveal
            reveal(hero)
        cd = inf.cooldown(rank) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0))
        kits = getattr(g, 'kits', None)
        kc = kits.call(hero, 'cast_cooldown', hero, inf, rank, cd) if kits is not None else None
        if kc is not None:
            cd = kc                                      # the kit's (Aurelion Sol's E: 0, its cooldown when it ends)
        mana = hero.mana_cost(slot)
        # [the replays: 590 of 654 spells' cast times are the data's; the other 64 (default 0.5 where the real one is
        # 0, ...) and every total time are taken from the real server's own 1215]
        tp = getattr(g, 'templates', None)
        real_cast, real_total = tp.cast_times(hero.name, inf.name) if tp is not None else (None, None)
        shown_cast = real_cast if real_cast is not None and real_cast >= 0 else max(0.0, inf.cast_time)
        shown_total = real_total if real_total is not None and real_total >= 0 else max(inf.total_time, shown_cast)
        cast_time = real_cast if real_cast is not None and real_cast >= 0 else (0.0 if inf.scripted else inf.cast_time)
        self.casts += 1
        cast_id, missile_id = g.new_net(), g.new_net()
        hero.facing = direction
        hero.reveal_until = t + 1.0
        if cast_time > 0 or not inf.targeting in SELF_TYPES:
            if hero.path:
                hero.stop()
            hero.cancel_attack()
        g.q += g.pk.cast(t, hero.net, inf.name, slot, self.casts, cast_id, missile_id, aim, end, here, direction,
                         shown_cast, shown_total, cd, mana, tgt.net if tgt else 0,
                         package=G.package_hash(hero.name), champion=hero.name)
        g.q += g.pk.face(hero, direction)
        ctx = dict(hero=hero, slot=slot, inf=inf, rank=rank, aim=aim, end=end, tgt=tgt, origin=here, direction=direction,
                   cast_id=cast_id, missile_id=missile_id, t0=t)
        kits = getattr(g, 'kits', None)
        if kits is not None:
            kits.call(hero, 'cast_begin', ctx)           # a kit's own state for this cast (core/kits)
        if getattr(g, 'passives', None) is not None:
            g.passives.on_cast(hero, slot)
        if getattr(g, 'statbuffs', None) is not None:
            g.statbuffs.on_cast(hero, slot, rank)
        if getattr(g, 'renewals', None) is not None:
            g.renewals.on_cast(hero)
        hero.cooldowns[slot] = t + max(cd, 0.5)          # before the template: a recast form it puts in the slot is free
        if slot < 4 and inf.name != hero.champ.spells[slot]:
            # a recast form (Garen's E again, a "...Cancel"): the first cast's lasting area stops with it
            zc = getattr(hero, 'zone_ctx', None)
            if zc is not None:
                zc['stop'] = True
                hero.zone_ctx = None
            for key, b in list(getattr(hero, 'buff_list', {}).items()):
                if key == (hero.champ.spells[slot], ENHANCER):
                    del hero.buff_list[key]
                    g.q += g.pk.buff_remove(hero.net, b['slot'], b['hash'])
        bb = getattr(g, 'bb', None)
        if bb is not None and bb.handles(hero):
            # the champion runs on its BuildingBlocks scripts (core/bbengine.py): they do what the cast does
            if mana:
                hero.set_par(hero.par - mana)
            hero.casting_until = t + cast_time
            hero.refresh_bits()
            g.at(hero.cooldowns[slot] + 0.02, lambda t2, hero=hero: hero.refresh_bits())
            bb.cast(hero, inf.name, tgt, rank, ctx=ctx)
            if tp is not None:
                # what the engine itself sends with a cast (its cooldown, the animations, the autocast state ...) is
                # not the scripts': those come from the real casts' templates
                from .bbengine import ENGINE_PIDS
                tp.play(hero, inf.name, aim, end, here, tgt, cast_id, missile_id, sctx=ctx, only=ENGINE_PIDS)
            if inf.targeting in SELF_TYPES and not inf.own_missile and not inf.missile_name and not inf.aoe and not inf.name.startswith(('GarenE', 'Aatrox')):
                return
        played = tp.play(hero, inf.name, aim, end, here, tgt, cast_id, missile_id, sctx=ctx) if tp is not None else None
        ctx['tpl'] = played
        ctx['move'] = tp.movement(hero.name, inf.name) if played is not None else None
        has_fx = played is not None and any(e['pid'] == 10 for e in tp.core(played.tpl))
        if g.fx is not None and slot < 4 and not has_fx:
            g.fx.on_cast(hero, slot, inf, rank, aim if inf.targeting not in SELF_TYPES else None, tgt)
        if mana:
            hero.set_par(hero.par - mana)
        hero.casting_until = t + cast_time
        hero.refresh_bits()
        g.at(hero.cooldowns[slot] + 0.02, lambda t2, hero=hero: hero.refresh_bits())
        mv = ctx['move']
        if mv is not None and mv[0] == 'dash' and mv[1] < cast_time - 0.02 and not ctx.get('kit_dash'):
            # [the replays] the real dash begins before the cast time is over (Akali's flip at +0.13 of 0.25)
            ctx['dashed'] = True
            gm = tp.geom(hero.name, inf.name)
            if tp.own_missile(hero.name, inf.name) is not None or tp.primary_missiles(hero.name, inf.name):
                ctx['dash_only'] = True
            g.at(t + mv[1], lambda t2: hero.alive and self.start_dash(ctx, (gm or {}).get('dash')))
        if cast_time > 0:
            g.at(t + cast_time, lambda t2: self.resolve(ctx))
        else:
            self.resolve(ctx)

    # ------------------------------------------------------------------ the cast time is over
    def resolve(self, c):
        g = self.g
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        if not hero.alive:
            return
        kits = getattr(g, 'kits', None)
        if kits is not None and kits.call(hero, 'resolve', c):
            return                                       # the champion's kit plays it (core/kits)
        here = hero.pos
        mv = c.get('move')
        if mv is not None and mv[0] == 'teleport':
            # [the replays] the real server teleports the champion (61 with a teleport id) this long after the cast
            dest = g.nav.nearest_free(*c['end']) or c['end']
            if c['slot'] < 4 and inf.name != hero.champ.spells[c['slot']] and getattr(g, 'summons', None) is not None:
                # a recast form: to the unit the first cast made (Zed's shadow), which takes the champion's place
                mine = [u for u in g.units.values() if getattr(u, 'owner', None) is hero and u.alive and u.kind == 'summon']
                if mine:
                    shadow = max(mine, key=lambda u: u.net)
                    dest, old = shadow.pos, hero.pos
                    g.at(g.t + max(0.0, mv[1] - (g.t - c['t0'])), lambda t2, shadow=shadow, old=old: shadow.alive and shadow.teleport(old))
            delay = max(0.0, mv[1] - (g.t - c['t0']))
            g.at(g.t + delay, lambda t2: hero.alive and hero.blink(dest))
            return
        tp = g.templates if c.get('tpl') is not None else None
        gm = tp.geom(hero.name, inf.name) if tp is not None else None
        if inf.blink and tp is None:                     # no real cast to go by: the data's hint
            dest = g.nav.nearest_free(*c['end']) or c['end']
            hero.blink(dest)
            self.area(c, dest, max(inf.radius(rank), 150.0)) if inf.aoe else None
            return
        if tp is not None:
            # what the real server did after this spell [the replays] decides its kind, not the data's hints
            own = tp.own_missile(hero.name, inf.name) is not None
            if mv is not None and mv[0] == 'dash' and c['slot'] < 4 and inf.name != hero.champ.spells[c['slot']]:
                mine = [u for u in g.units.values() if getattr(u, 'owner', None) is hero and u.alive and u.kind == 'summon']
                if mine:
                    # a recast form: the champion and the unit the first cast made (Zed's shadow) change places
                    shadow = max(mine, key=lambda u: u.net)
                    dest, old = shadow.pos, hero.pos
                    ev = (gm or {}).get('dash') or {}
                    speed = ev.get('speed') if 100.0 <= (ev.get('speed') or 0.0) <= 6000.0 else 2500.0
                    c['dash_only'] = True
                    hero.path = None
                    hero.order = None
                    hero.dashing = True
                    g.q += g.pk.dash(g.t, hero, [hero.pos, dest], speed)
                    self.push_dash(hero, dest, speed, c)
                    shadow.teleport(old)
                    return
            if mv is not None and mv[0] == 'dash' and c.get('dashed'):
                if own:
                    self.launch_own(c, gm)
                elif inf.targeting in ('direction', 'Location', 'Cone') or inf.width > 0 or inf.cone > 0 or inf.aoe:
                    self.shape(c)
                return
            if mv is not None and mv[0] == 'dash':
                delay = max(0.0, mv[1] - (g.t - c['t0']))
                dash = (gm or {}).get('dash')
                if own or tp.primary_missiles(hero.name, inf.name):
                    c['dash_only'] = True                # the hit is the missile's; the dash follows it (a hook's pull)
                    if own:
                        self.launch_own(c, gm)
                elif inf.targeting in ('direction', 'Location', 'Cone') or inf.width > 0 or inf.cone > 0:
                    c['dash_only'] = True
                    self.shape(c)
                if delay > 0.02:
                    g.at(g.t + delay, lambda t2: hero.alive and self.start_dash(c, dash))
                else:
                    self.start_dash(c, dash)
                return
            if own:
                return self.launch_own(c, gm)
            if tp.primary_missiles(hero.name, inf.name):
                return                                   # its hits are its missiles' (templates.missile)
            # [the replays] a spell with no missile and no movement hits when the real server's damage fell
            when = tp.hit_time(hero.name, inf.name)
            if when is not None:
                c['timed'] = True
                if when - (g.t - c['t0']) > 0.03:
                    g.at(c['t0'] + when, lambda t2: hero.alive and self.shape(c))
                    return
        elif inf.dash:
            return self.start_dash(c)
        self.shape(c)

    def shape(self, c):
        """whom the spell hits, by its kind of aim [data]"""
        g = self.g
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        here = hero.pos
        bb = getattr(g, 'bb', None)
        if bb is not None and bb.handles(hero) and bb.rt.has(inf.name, 'TargetExecuteBuildingBlocks'):
            pass
        elif c.get('tpl') is not None and g.templates.makes_units(hero.name, inf.name) and \
                not g.templates.direct_damage(hero.name, inf.name):
            return                                       # its effect is the unit the template creates (summons.py)
        if inf.empower:
            dmg, dtype = self.damage_of(hero, inf, rank)
            hero.empowered = {'inf': inf, 'rank': rank, 'until': g.t + 5.0, 'damage': dmg, 'type': dtype}
            hero.attack_ready = g.t
            self.self_effects(c)
            return
        tg = inf.targeting
        if tg in SELF_TYPES:
            self.self_effects(c)
            radius = inf.radius(rank)
            if radius > 0 and (inf.aoe or inf.dot or tg == 'SelfAoe'):
                if inf.dot:
                    self.zone(c, None, radius, follow=hero)
                else:
                    self.area(c, here, radius)
            return
        if tg in LINE_TYPES or (tg in PLACE_TYPES and inf.width > 0 and inf.missile_speed > 0 and not inf.aoe):
            if inf.missile_speed > 0:
                return self.launch(c, here, c['direction'], inf.range(rank))
            return self.line(c, here, c['end'])
        if tg == 'Cone':
            return self.cone(c)
        if tg in PLACE_TYPES:
            delay = 0.0 if c.get('timed') else dist(here, c['aim']) / inf.missile_speed if inf.missile_speed > 0 else AREA_DELAY
            radius = inf.radius(rank) or 150.0
            if inf.dot:
                g.at(g.t + delay, lambda t2: self.zone(c, c['aim'], radius))
            else:
                g.at(g.t + delay, lambda t2: self.area(c, c['aim'], radius))
            return
        tgt = c['tgt']
        if tgt is None or not tgt.alive:
            return
        if tgt.team == hero.team:
            return self.ally_effects(c, tgt)
        if inf.missile_speed > 0 and dist(here, tgt.pos) > 250.0:
            return self.launch(c, here, c['direction'], 0.0, target=tgt)
        self.hit(c, tgt)

    # ------------------------------------------------------------------ shapes
    def enemies(self, hero):
        return [o for o in self.g.units.values() if o.alive and o.targetable and o.team != hero.team and not o.is_structure
                and o.kind != 'plant']

    def area(self, c, center, radius):
        for o in self.enemies(c['hero']):
            if dist(o.pos, center) <= radius + o.radius:
                self.hit(c, o)

    def cone(self, c):
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        half = math.radians(inf.cone or 25.0)
        reach = inf.range(rank)
        for o in self.enemies(hero):
            vx, vz = o.pos[0] - hero.pos[0], o.pos[1] - hero.pos[1]
            vd = math.hypot(vx, vz)
            if 0 < vd <= reach + o.radius:
                cosang = (vx * c['direction'][0] + vz * c['direction'][1]) / vd
                if math.acos(max(-1.0, min(1.0, cosang))) <= half:
                    self.hit(c, o)

    def line(self, c, a, b):
        inf = c['inf']
        w = inf.width or 60.0
        found = []
        for o in self.enemies(c['hero']):
            dd, f = _point_segment(o.pos, a, b)
            if dd <= w / 2 + o.radius:
                found.append((f, o))
        found.sort(key=lambda x: x[0])
        for f, o in (found[:1] if inf.stops_first else found):
            self.hit(c, o)

    def zone(self, c, center, radius, follow=None):
        """damage over time in an area: the spell's damage in ticks every half second for its duration [a]"""
        inf, rank, hero = c['inf'], c['rank'], c['hero']
        dur = inf.data_value(('Duration', 'BuffDuration', 'ZoneDuration', 'SpinDuration', 'TotalDuration'), rank) or 3.0
        ticks = max(1, int(round(dur / 0.5)))
        total, dtype = inf.damage(hero, rank)
        per = total / ticks if total > 0 else 0.0
        if per <= 0:
            total, dtype = self.damage_of(hero, inf, rank)       # the real server's own amount of one tick
            per = total
        else:
            dtype = self.damage_of(hero, inf, rank)[1]
        cc = dict(c, tick=per, tick_type=dtype)
        if follow is not None:
            self.buff(hero, hero, inf, ENHANCER, dur)
            hero.zone_ctx = cc
        n = [0]

        def tick(t2):
            i, n[0] = n[0], n[0] + 1
            if (hero.alive or follow is None) and not cc.get('stop'):
                self.area(dict(cc, first=(i == 0)), follow.pos if follow is not None else center, radius)
        # [m] a script's timer: its ticks on the script's own updates (0.5 s -> 0.535 / 0.535 / ... with the rest kept)
        self.g.script_timer(0.5, tick, count=ticks, alive=lambda: not cc.get('stop'))

    # ------------------------------------------------------------------ missiles
    def launch(self, c, start, direction, reach, target=None):
        g = self.g
        hero, inf = c['hero'], c['inf']
        mid = c['missile_id']
        if c.get('tpl') is not None:
            # [the replays] this spell's real casts showed no missile of the cast's own (938) and no missile spell
            # (223: those are the template's): it hits at once
            if target is not None:
                return self.hit(c, target)
            return self.line(c, start, (start[0] + direction[0] * reach, start[1] + direction[1] * reach))
        speed = inf.missile_speed or 1200.0
        if inf.own_missile or not inf.missile_name:
            g.q += g.pk.missile_launch(hero, mid)
        else:
            end = target.pos if target is not None else (start[0] + direction[0] * reach, start[1] + direction[1] * reach)
            mid = g.new_net()
            self.casts += 1
            g.q += g.pk.spell_in_slot(hero.net, 0x2d, inf.missile_name)
            g.q += g.pk.spell_missile(g.t, mid, hero.net, inf.missile_name, 0x2d, self.casts, g.new_net(), start, end, speed,
                                      package=G.package_hash(hero.name), champion=hero.name, target=target.net if target else 0)
            g.q += g.pk.missile_launch(hero, mid)
        self.missiles.append((Missile(mid, hero, inf, c['rank'], start, direction, speed, reach, target, inf.width or 60.0), c))

    def launch_own(self, c, gm):
        """the cast's own missile leaves (938 names the missile id the 1215 carried; the client builds it from the
        spell's data) [the replays: 39 of 39 at the end of the cast time]"""
        g = self.g
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        ms = mspec(inf.sd)
        here = hero.pos
        tgt = c['tgt'] if c['tgt'] is not None and c['tgt'].alive and ms['tracks'] and inf.targeting in ('Target', 'TargetOrLocation') else None
        reach = (gm or {}).get('reach') or {}
        on_end = None
        if tgt is not None:
            length = 0.0
        elif reach and reach['hi'] - reach['lo'] <= 40.0 and reach['med'] > 50.0:
            length = reach['med']                        # [the replays] the same length in every cast: a line
        elif ms['project'] or inf.targeting in LINE_TYPES:
            length = ms['range'] if ms['range'] > 0 else inf.range(rank)
        else:
            length = max(1.0, dist(here, c['aim']))      # it flies to the aimed place
            if ms['on_complete'] or not ms['collide']:
                radius = inf.radius(rank) or 150.0
                on_end = lambda p, c=c, radius=radius: self.area(c, p, radius)
        g.q += g.pk.missile_launch(hero, c['missile_id'])
        self.missiles.append((Missile(c['missile_id'], hero, inf, rank, here, c['direction'], ms['speed'] or inf.missile_speed or 1200.0,
                                      length, tgt, ms['width'] or inf.width or 60.0, ms['accel'], ms['vmin'], ms['vmax'],
                                      stops=ms['stops'], collide=ms['collide'] or on_end is None, on_end=on_end), c))

    def sweep(self, m, c, a, b):
        """the enemies a missile meets between a and b are hit -> True when one stops it"""
        g = self.g
        found = []
        for o in self.enemies(m.owner):
            if o.net in m.hit:
                continue
            dd, f = _point_segment(o.pos, a, b)
            if dd <= m.width / 2 + o.radius:
                found.append((f, o))
        found.sort(key=lambda x: x[0])
        for f, o in found:
            m.hit.add(o.net)
            g.q += g.pk.missile_hit(m.net, o.net, o.pos)
            c['missile'] = m
            self.hit(c, o)
            if m.stops:
                return True
        return False

    def move_missiles(self, t, dt):
        g = self.g
        keep = []
        for m, c in self.missiles:
            if m.accel:
                m.speed = max(m.vmin, min(m.vmax or 1e9, m.speed + m.accel * dt))
            step = m.speed * dt
            if m.target is not None:
                tg = m.target
                if not tg.alive:
                    g.q += g.pk.missile_end(m.net)
                    continue
                d = dist(m.pos, tg.pos)
                arrive = d <= step + tg.radius
                nxt = tg.pos if arrive else (m.pos[0] + (tg.pos[0] - m.pos[0]) / d * step, m.pos[1] + (tg.pos[1] - m.pos[1]) / d * step)
                if m.returning and m.collide:
                    self.sweep(m, c, m.pos, nxt)         # on its way back to its owner it hits what it meets
                if arrive:
                    if not m.returning:
                        g.q += g.pk.missile_hit(m.net, tg.net, tg.pos)
                        c['missile'] = m
                        self.hit(c, tg)
                    g.q += g.pk.missile_end(m.net)
                    continue
                m.pos = nxt
                keep.append((m, c))
                continue
            step = min(step, m.left)
            nxt = (m.pos[0] + m.dir[0] * step, m.pos[1] + m.dir[1] * step)
            stopped = m.collide and self.sweep(m, c, m.pos, nxt)
            m.pos = nxt
            m.left -= step
            if stopped or m.left <= 0.5:
                if m.on_end is not None and not stopped:
                    m.on_end(m.pos)
                g.q += g.pk.missile_end(m.net)
                continue
            keep.append((m, c))
        self.missiles = keep

    # ------------------------------------------------------------------ dashes and blinks
    def start_dash(self, c, ev=None):
        """ev: the real dash of this spell [the replays' 1140s: its speed, its length over the casts, its angle from
        the cast's direction (Akali's E flips backwards)]"""
        g = self.g
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        tgt = c['tgt']
        rng = inf.range(rank)
        if ev and not (tgt is not None and tgt.alive and inf.targeting in ('Target', 'TargetOrLocation')):
            ln = ev['len']
            ang = ev['angle'] if ev.get('angle_spread', 0.0) <= 30.0 else 0.0
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            dx, dz = c['direction']
            d2 = (dx * ca - dz * sa, dx * sa + dz * ca)
            if ln['hi'] - ln['lo'] <= 80.0:
                length = ln['med']                       # the same length in every cast
            else:
                length = min(max(dist(hero.pos, c['aim']), ln['lo'] if abs(ang) > 90.0 else 0.0), ln['hi'])
            dest = (hero.pos[0] + d2[0] * length, hero.pos[1] + d2[1] * length)
            dest = g.nav.nearest_free(*dest) or hero.pos
            speed = ev['speed'] if 100.0 <= ev['speed'] <= 6000.0 else DEFAULT_DASH_SPEED
            if dist(hero.pos, dest) < 5.0:
                return self.land(c, dest)
            hero.path = None
            hero.order = None
            hero.dashing = True
            g.q += g.pk.dash(g.t, hero, [hero.pos, dest], speed)
            self.push_dash(hero, dest, speed, c)
            hero.casting_until = max(hero.casting_until, g.t + dist(hero.pos, dest) / speed)
            return
        if tgt is not None and tgt.alive and inf.targeting in ('Target', 'TargetOrLocation'):
            d = dist(hero.pos, tgt.pos) or 1.0
            stop = max(0.0, d - (hero.radius + tgt.radius))
            dest = (hero.pos[0] + (tgt.pos[0] - hero.pos[0]) / d * stop, hero.pos[1] + (tgt.pos[1] - hero.pos[1]) / d * stop)
        else:
            d = dist(hero.pos, c['aim'])
            f = min(1.0, rng / d) if d > 0 and rng > 0 else 1.0
            dest = (hero.pos[0] + (c['aim'][0] - hero.pos[0]) * f, hero.pos[1] + (c['aim'][1] - hero.pos[1]) * f)
        dest = g.nav.nearest_free(*dest) or hero.pos
        speed = (ev['speed'] if ev and 100.0 <= ev['speed'] <= 6000.0 else None) or \
            next((inf.calc(calc, hero, rank) for tag, calc in inf.effects if tag == T_DASH_SPEED), None) or \
            (inf.missile_speed if 400 <= inf.missile_speed <= 3500 else DEFAULT_DASH_SPEED)
        if dist(hero.pos, dest) < 5.0:
            return self.land(c, dest)
        hero.path = None
        hero.order = None
        hero.dashing = True
        g.q += g.pk.dash(g.t, hero, [hero.pos, dest], speed)
        self.push_dash(hero, dest, speed, c)
        hero.casting_until = max(hero.casting_until, g.t + dist(hero.pos, dest) / speed)

    def land(self, c, dest):
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        hero.dashing = False
        if c.get('dash_only'):
            return
        tgt = c['tgt']
        if tgt is not None and tgt.alive and tgt.team != hero.team and inf.targeting in ('Target', 'TargetOrLocation'):
            self.hit(c, tgt)
        elif inf.aoe or inf.radius(rank) > 0:
            met = c.get('dash_hits') or ()
            for o in self.enemies(hero):
                if o.net not in met and dist(o.pos, dest) <= max(inf.radius(rank), 150.0) + o.radius:
                    self.hit(c, o)

    def push_dash(self, hero, dest, speed, c):
        """a unit moves along one dash at a time: a new one replaces the one under way (two at once pulled the
        champion both ways and it never landed - stuck 'dashing', never attacking again)"""
        self.dashes = [d for d in self.dashes if d[0] is not hero]
        c['dash_until'] = self.g.t + dist(hero.pos, dest) / max(1.0, speed) + 0.5
        self.dashes.append([hero, dest, speed, c])

    def drop_dash(self, hero):
        """the champion is put elsewhere (a teleport, the golden test's place sync): its dash is over where it is"""
        if any(d[0] is hero for d in self.dashes):
            self.dashes = [d for d in self.dashes if d[0] is not hero]
        hero.dashing = False

    def move_dashes(self, t, dt):
        keep = []
        for d in self.dashes:
            hero, dest, speed, c = d
            if not hero.alive:
                hero.dashing = False
                continue
            left = dist(hero.pos, dest)
            step = speed * dt
            nxt = dest if left <= step else (hero.pos[0] + (dest[0] - hero.pos[0]) / left * step, hero.pos[1] + (dest[1] - hero.pos[1]) / left * step)
            inf = c['inf']
            if not c.get('dash_only') and inf.targeting not in ('Target', 'TargetOrLocation') + SELF_TYPES:
                # [a] a dash aimed at a place hits the enemies it passes through, each once
                met = c.setdefault('dash_hits', set())
                for o in self.enemies(hero):
                    if o.net not in met and _point_segment(o.pos, hero.pos, nxt)[0] <= max(inf.width, 2.0 * hero.radius) / 2 + o.radius:
                        met.add(o.net)
                        self.hit(c, o)
            if left <= step:
                hero.pos = dest
                self.land(c, dest)
            elif t > c.get('dash_until', 1e9):
                self.land(c, hero.pos)                   # it could not get there (pushed, held): it lands where it is
            else:
                hero.pos = nxt
                keep.append(d)
        self.dashes = keep

    # ------------------------------------------------------------------ what a hit does
    def hit(self, c, tgt):
        g = self.g
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        if not tgt.alive:
            return
        c['hits'] = c.get('hits', 0) + 1
        tp = getattr(g, 'templates', None)
        if tp is not None and c.get('tpl') is not None:
            tp.on_cast_hit(c['tpl'], tgt)
        ps = getattr(g, 'passives', None)
        if ps is not None and hero.is_hero:
            ps.on_spell_hit(hero, tgt)
        kits = getattr(g, 'kits', None)
        if kits is not None and kits.call(hero, 'spell_hit', c, tgt):
            return                                       # the champion's kit deals it (core/kits)
        bb = getattr(g, 'bb', None)
        if bb is not None and bb.handles(hero) and bb.spell_hit(hero, inf.name, tgt, rank):
            return                                       # the BuildingBlocks script deals it (core/bbengine.py)
        if 'tick' in c:
            amount, dtype = c['tick'], c.get('tick_type', P.MAGIC)
        else:
            amount, dtype = self.damage_of(hero, inf, rank)
        tp = getattr(g, 'templates', None)
        if tp is not None and tp.show_hit(hero, inf.name, tgt):
            pass                                         # the real server's own hit effects (the template)
        elif g.fx is not None and c.get('slot', 9) < 4:
            g.fx.on_hit(hero, c['slot'], tgt)
        if amount > 0:
            source = P.SRC_PERIODIC if 'tick' in c else P.SRC_DIRECT
            g.deal(hero, tgt, amount, dtype, basic=False, source=source, spell_hash=P.damage_hash(inf.name))
        if tgt.alive and c.get('first', True):
            self.effects(c, tgt)

    def damage_of(self, hero, inf, rank):
        """(amount, type) a hit of this spell deals: the amount from the spell's data; when the data's calculation
        cannot be worked out (None / 0) and the real server did deal damage under this spell's name, the amount it dealt
        in the replays [a: of whatever level and items those champions had]; the type the real server used"""
        amount, dtype = inf.damage(hero, rank)
        tp = getattr(self.g, 'templates', None)
        real = tp.real_damage(hero.name, inf.name) if tp is not None and hero.is_hero else None
        if hero.is_hero:
            wd = inf.wiki_damage(hero, rank)
            plain = ((inf.wiki() or {}).get('damage') or {}).get('attribute') in ('Magic Damage', 'Physical Damage', 'True Damage')
            # [m 10-13: 33 spells without bot data, against the replays' amounts] a calculation guessed by its name is
            # near the real damage less often than the wiki's formula (0.72 / 0.79): the wiki's wins there
            guessed = inf.dmg_calc is None and amount > 0
            if wd is not None and wd[0] > 0 and (amount <= 0 or guessed or (plain and amount > 1.5 * wd[0])):
                # nothing from the data: the wiki's formula (before a replay's bare number). And [a] a data total half
                # again over the wiki's plain hit is two hits summed (Lee Sin's Q + its recast, Anivia's Q + its
                # burst): one hit is the wiki's
                amount, dtype = wd
        if real is not None:
            if amount <= 0:
                amount = real[0]
            if real[1] in (0, 1, 2):
                dtype = real[1]
        return amount, dtype

    def effects(self, c, tgt):
        """the spell's effects on an enemy it hits: the template's buffs (what the real server gave the units this
        spell hit) when there is one, else the bot data's"""
        g, t = self.g, self.g.t
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        tp = getattr(g, 'templates', None)
        hb = tp.hit_buffs(hero.name, inf.name) if tp is not None else []
        if hb:
            return self.template_effects(c, tgt, hb)
        tpl = tp.of(hero.name, inf.name) if tp is not None else None
        if tpl is not None and tpl.get('samples', 0) >= 12:
            # [the replays] in a dozen or more real casts the units this spell hit were given no crowd control: what
            # the data lists is conditional (a full charge, the third cast in a row), not what a plain hit does
            return
        vals = {}
        for tag, calc in inf.effects:
            v = inf.calc(calc, hero, rank)
            if v is not None:
                vals[tag] = v
        if not inf.effects:
            named = inf.named_control(rank)
            if named.get('knockup'):
                self.cc(hero, tgt, inf, KNOCKUP, min(named['knockup'], 3.0), stun=True)
            if named.get('stun'):
                self.cc(hero, tgt, inf, STUN, named['stun'], stun=True)
            if named.get('root'):
                self.cc(hero, tgt, inf, SNARE, named['root'], root=True)
            if named.get('silence'):
                self.cc(hero, tgt, inf, SILENCE, named['silence'], silence=True)
            if named.get('slow'):
                self.slow(hero, tgt, inf, named['slow'][0], min(named['slow'][1], 5.0))
            return
        root, disarm, silence = vals.get(T_ROOT, 0.0), vals.get(T_DISARM, 0.0), vals.get(T_SILENCE, 0.0)
        up = vals.get(T_KNOCKUP, 0.0)
        if up > 0:
            self.cc(hero, tgt, inf, KNOCKUP, min(up, 3.0), stun=True)
        elif root > 0 and disarm > 0 and silence > 0:
            self.cc(hero, tgt, inf, STUN, min(root, 5.0), stun=True)
        else:
            if 0 < root <= 6.0:
                self.cc(hero, tgt, inf, SNARE, root, root=True)
            if 0 < silence <= 6.0:
                self.cc(hero, tgt, inf, SILENCE, silence, silence=True)
            if 0 < disarm <= 6.0:
                self.cc(hero, tgt, inf, DISARM, disarm, disarm=True)
        slow = vals.get(T_SLOW)
        if slow is not None and slow != 0:
            pct = abs(slow) / 100.0 if abs(slow) > 1.0 else abs(slow)
            if 0 < pct < 1.0 and (slow < 0 or 'slow' in inf.name.lower() or abs(slow) > 1.0):
                dur = inf.data_value(('SlowDuration', 'Duration', 'SlowTime'), rank) or DEFAULT_SLOW_TIME
                self.slow(hero, tgt, inf, pct, min(dur, 5.0))
        back = vals.get(T_KNOCKBACK, 0.0)
        if back > 50 and tgt.can_move and not tgt.is_structure:
            d = dist(hero.pos, tgt.pos) or 1.0
            dest = (tgt.pos[0] + (tgt.pos[0] - hero.pos[0]) / d * back, tgt.pos[1] + (tgt.pos[1] - hero.pos[1]) / d * back)
            dest = g.nav.nearest_free(*dest) or tgt.pos
            tgt.path = None
            g.q += g.pk.dash(t, tgt, [tgt.pos, dest], 1200.0)
            tgt.pos = dest
            tgt.cc_until = max(tgt.cc_until, t + back / 1200.0)

    def template_effects(self, c, tgt, buffs):
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        for btype, h, dur in buffs:
            dur = dur if 0 < dur < 60 else 1.0
            kind = CC_TYPES.get(btype)
            if kind and kind != 'slow':
                # the kind is the real server's; its length at this rank is the wiki's when it gives one (a replay's
                # is of whatever rank that cast had)
                wsec = inf.wiki_cc(kind, rank)
                if wsec is not None and 0 < wsec <= 6.0:
                    dur = wsec
            if kind in ('stun', 'fear', 'charm', 'taunt', 'suppress', 'flee', 'asleep'):
                self.cc(hero, tgt, inf, btype, dur, stun=True, name_hash=h)
            elif kind in ('knockup', 'knockback'):
                self.cc(hero, tgt, inf, btype, min(dur, 3.0), stun=True, name_hash=h)
            elif kind == 'snare':
                self.cc(hero, tgt, inf, btype, dur, root=True, name_hash=h)
            elif kind == 'silence':
                self.cc(hero, tgt, inf, btype, dur, silence=True, name_hash=h)
            elif kind == 'disarm':
                self.cc(hero, tgt, inf, btype, dur, disarm=True, name_hash=h)
            elif kind == 'slow':
                named = inf.named_control(rank).get('slow')
                wpct, wsec = inf.wiki_cc('slow', rank), inf.wiki_cc('slow_time', rank)
                pct = named[0] if named else (wpct / 100.0 if wpct and 0 < wpct < 100 else 0.3)
                self.slow(hero, tgt, inf, pct, wsec if wsec and 0 < wsec <= 6.0 else dur, name_hash=h)
            elif not tgt.is_structure:
                self.buff(hero, tgt, inf, btype, dur, key=('tpl', h), name_hash=h)

    def self_effects(self, c):
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        for tag, calc in inf.effects:
            v = inf.calc(calc, hero, rank)
            if v is None:
                continue
            if tag == T_HEAL and v > 0:
                hero.set_hp(hero.hp + v)
            elif tag == 2 and 0 < v <= 1.0:              # a self haste given as a share (Garen Q 0.35) [a: 2.5 s]
                dur = inf.data_value(('MoveSpeedDuration', 'HasteDuration', 'Duration', 'BuffDuration'), rank) or 2.5
                self.haste(hero, inf, v, min(dur, 8.0))

    def ally_effects(self, c, tgt):
        hero, inf, rank = c['hero'], c['inf'], c['rank']
        for tag, calc in inf.effects:
            v = inf.calc(calc, hero, rank)
            if v is not None and tag == T_HEAL and v > 0:
                tgt.set_hp(tgt.hp + v)

    def on_basic_hit(self, src, tgt, dealt):
        """an empowered attack lands: the spell's damage on top, its effects"""
        ps = getattr(self.g, 'passives', None)
        if ps is not None:
            ps.on_basic_hit(src, tgt)
        e = getattr(src, 'empowered', None)
        if not e or self.g.t > e['until']:
            src.empowered = None
            return
        src.empowered = None
        c = dict(hero=src, inf=e['inf'], rank=e['rank'], tgt=tgt)
        if e['damage'] > 0 and tgt.alive:
            self.g.deal(src, tgt, e['damage'], e['type'], basic=False, source=P.SRC_PERIODIC, spell_hash=P.damage_hash(e['inf'].name))
        if tgt.alive:
            self.effects(c, tgt)

    # ------------------------------------------------------------------ buffs the client is told about
    def buff_slot(self, u):
        used = {b['slot'] for b in getattr(u, 'buff_list', {}).values()}
        s = 0x30 if u.is_hero else 1
        while s in used:
            s += 1
        return s

    def buff(self, src, tgt, inf, btype, duration, key=None, undo=None, name_hash=None):
        g = self.g
        if not hasattr(tgt, 'buff_list'):
            tgt.buff_list = {}
        key = key or (inf.name, btype)
        h = name_hash if name_hash is not None else P.elf(inf.name)
        old = tgt.buff_list.get(key)
        slot = old['slot'] if old else self.buff_slot(tgt)
        if old and old.get('undo'):
            old['undo']()
        # [m] a buff's start is only told about a unit in sight (it follows when the unit comes into sight); its end
        # is told wherever the unit is, if the start was
        known = g.vision is None or not g.vision.hidden(tgt)
        package = G.package_hash(src.name)
        tgt.buff_list[key] = {'slot': slot, 'until': g.t + duration, 'hash': h, 'undo': undo,
                              'known': known, 'args': (src.net, slot, btype, h, package)}
        if known:
            g.q += g.pk.buff_add(tgt.net, src.net, slot, btype, h, duration, package=package)
        self.buffs.append([g.t + duration, tgt, key])
        self.renew_on_updates(tgt, key)

    def renew_on_updates(self, u, key):
        """[m: tools/buff_refresh16.py, 32 buffs] a buff the real server renews on every script update while it lasts
        (an area's slow / poison, an aura): a 282 with the measured duration and count every 0.267 s, the first one
        update after the 435, until the buff is gone"""
        b = getattr(u, 'buff_list', {}).get(key)
        r = buff_refresh().get(P.u32(b['hash'])) if b else None
        from . import renewals
        if r is None or P.u32(b['hash']) in renewals.table():
            return                                       # core/renewals.py renews it by its measured causes
        g = self.g
        from .game import SCRIPT_UPDATE

        def tick(t, b=b):
            cur = getattr(u, 'buff_list', {}).get(key)
            if cur is not b or not u.alive:
                return
            if cur.get('known', True):
                g.q += g.pk.buff_count(u.net, b['slot'], b['args'][0], r['dur'], r['count'])
            g.after_frames(8, tick)
        g.after_frames(8, tick)

    def expire(self, t):
        keep = []
        for b in self.buffs:
            until, u, key = b
            cur = getattr(u, 'buff_list', {}).get(key)
            if cur is None or cur['until'] > until + 1e-6:
                continue                          # renewed: a later entry ends it
            if t >= until or not u.alive:
                del u.buff_list[key]
                if cur.get('undo'):
                    cur['undo']()
                if cur.get('known', True):
                    self.g.tell_all(self.g.pk.buff_remove(u.net, cur['slot'], cur['hash']))
            else:
                keep.append(b)
        self.buffs = keep

    def action_state(self, u):
        t = self.g.t
        if not u.is_hero:
            return
        state = ACTION_NORMAL
        if t < u.cc_until:
            state &= ~7
        if t < u.root_until:
            state &= ~4
        if t < getattr(u, 'silence_until', 0.0):
            state &= ~2
        if t < getattr(u, 'disarm_until', 0.0):
            state &= ~1
        on, off = getattr(u, 'tpl_bits', (0, 0))
        state = (state | on) & ~off
        u.set('ActionState', state)

    def cc(self, src, tgt, inf, btype, duration, stun=False, root=False, silence=False, disarm=False, name_hash=None):
        g, t = self.g, self.g.t
        if tgt.is_structure:
            return
        if tgt.is_hero and tgt.bonus.get('tenacity') and btype != KNOCKUP:
            duration *= 1.0 - min(0.9, tgt.bonus['tenacity'])
        if stun:
            tgt.cc_until = max(tgt.cc_until, t + duration)
            tgt.windup_end = None
        if root:
            tgt.root_until = max(tgt.root_until, t + duration)
        if silence:
            tgt.silence_until = max(getattr(tgt, 'silence_until', 0.0), t + duration)
        if disarm:
            tgt.disarm_until = max(getattr(tgt, 'disarm_until', 0.0), t + duration)
            tgt.attack_ready = max(tgt.attack_ready, t + duration)
        if (stun or root) and tgt.path:
            tgt.stop()
            if tgt.is_hero:
                tgt.order = None
        if tgt.is_hero:
            self.pending.pop(tgt.net, None)
        if stun and btype in (8, 23, 22, 29) and not tgt.is_structure and src is not tgt:
            # LoL's own rule for these: charmed (23) and taunted (8) units walk to the caster, feared (22) and
            # fleeing (29) ones away from it, for as long as it holds [a: a charmed / feared unit at 35 % speed]
            d = dist(src.pos, tgt.pos) or 1.0
            if btype in (8, 23):
                goal = src.pos
            else:
                goal = (tgt.pos[0] + (tgt.pos[0] - src.pos[0]) / d * 400.0, tgt.pos[1] + (tgt.pos[1] - src.pos[1]) / d * 400.0)
                goal = g.nav.nearest_free(*goal) or tgt.pos
            tgt.forced_until = t + duration
            if btype != 8:
                slows = getattr(tgt, 'slows', None)
                if slows is None:
                    slows = tgt.slows = {}
                slows[('forced', inf.name)] = 0.65
                self.respeed(tgt)

                def unslow(t2, tgt=tgt, key=('forced', inf.name)):
                    tgt.slows.pop(key, None)
                    self.respeed(tgt)
                g.at(t + duration, unslow)
            tgt.target = None
            tgt.path_to(goal)
            g.at(t + duration, lambda t2, tgt=tgt: tgt.alive and tgt.stop())
        self.action_state(tgt)
        self.buff(src, tgt, inf, btype, duration, undo=lambda tgt=tgt: g.at(g.t + 0.01, lambda t2: self.action_state(tgt)),
                  name_hash=name_hash, key=(inf.name, btype, name_hash) if name_hash is not None else None)
        self.held(src, tgt, inf, duration)
        if g.fx is not None:                             # the mark every stun / silence wears [the shared particles]
            if stun and btype != KNOCKUP:
                g.fx.shared('LOC_Stun', src, tgt, lasting=duration, old='shared')
            elif silence:
                g.fx.shared('LOC_Silence', src, tgt, lasting=duration)

    def slow(self, src, tgt, inf, pct, duration, name_hash=None):
        if tgt.is_structure:
            return
        slows = getattr(tgt, 'slows', None)
        if slows is None:
            slows = tgt.slows = {}

        def undo(tgt=tgt, name=inf.name):
            tgt.slows.pop(name, None)
            self.respeed(tgt)
        # the buff first: renewing it runs the old one's undo, which must not take away the new slow
        self.buff(src, tgt, inf, SLOW, duration, undo=undo, name_hash=name_hash)
        slows[inf.name] = pct
        self.respeed(tgt)
        self.held(src, tgt, inf, duration)
        if self.g.fx is not None:
            self.g.fx.shared('Global_Slow', src, tgt, lasting=duration, old='shared')

    def held(self, src, tgt, inf, duration):
        fx = self.g.fx
        if fx is not None and src.is_hero and inf.name in inf.champ.spells[:4] and src.spell_name(inf.champ.spells.index(inf.name)) == inf.name:
            fx.on_held(src, inf.champ.spells.index(inf.name), tgt, duration)

    def haste(self, hero, inf, pct, duration):
        hastes = getattr(hero, 'hastes', None)
        if hastes is None:
            hastes = hero.hastes = {}
        hastes[inf.name] = pct

        def undo(hero=hero, name=inf.name):
            hero.hastes.pop(name, None)
            self.respeed(hero)
        self.respeed(hero)
        tp = getattr(self.g, 'templates', None)
        if tp is not None and HASTE in tp.self_buff_types(hero.name, inf.name):
            # the template sends the real server's own haste buff (its name, its time): only the speed is ours
            self.g.at(self.g.t + duration, lambda t2: undo())
            return
        self.buff(hero, hero, inf, HASTE, duration, undo=undo)
        if self.g.fx is not None:                        # [m] Global_Haste: nobody's, the global package
            self.g.fx.shared('Global_Haste', None, hero, lasting=duration)

    def respeed(self, u):
        """the unit's speed with its strongest slow and its hastes; a walking unit is given its path again"""
        slow = max(getattr(u, 'slows', {}).values(), default=0.0)
        haste = sum(getattr(u, 'hastes', {}).values())
        u.speed_mult = (1.0 - slow) * (1.0 + haste)
        u.set('mMoveSpeed', u.speed)
        if u.path and u.alive:
            self.g.q_moves.append(self.g.pk.move_entry(u.net, [u.pos] + list(u.path), u.speed))

    # ------------------------------------------------------------------ summoner spells, recall
    def summoner(self, hero, slot, aim, target):
        from . import summoners
        return summoners.cast(self, hero, slot, aim, target)

    def recall(self, hero):
        from . import summoners
        return summoners.recall(self, hero)

    # ------------------------------------------------------------------ the frame
    def tick(self, t, dt):
        if self.missiles:
            self.move_missiles(t, dt)
        if self.dashes:
            self.move_dashes(t, dt)
        if self.buffs:
            self.expire(t)
        if self.pending:
            for net, (slot, aim, target) in list(self.pending.items()):
                hero = self.g.units.get(net)
                if hero is None or not hero.alive or not hero.order or hero.order[0] != 'cast':
                    self.pending.pop(net, None)          # another order came: the cast is forgotten
                    continue
                tgt = self.g.units.get(target) if target else None
                if target and (tgt is None or not tgt.alive):
                    self.pending.pop(net, None)
                    hero.order = None
                    continue
                inf = info(hero.champ, hero.spell_name(slot))
                goal = tgt.pos if tgt is not None else aim
                need = inf.range(hero.spell_levels[slot]) + (hero.radius + tgt.radius if tgt is not None else 0.0)
                if dist(hero.pos, goal) <= need:
                    self.pending.pop(net, None)
                    hero.order = None
                    self.g.log(self.cast(hero, slot, goal, target))
                elif not hero.path:
                    hero.path_to(goal)


def _point_segment(p, a, b):
    ax, az = a
    dx, dz = b[0] - ax, b[1] - az
    L2 = dx * dx + dz * dz
    f = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / L2))
    return math.hypot(p[0] - (ax + f * dx), p[1] - (az + f * dz)), f


def setup(game, session=None):
    game.spells = Spells(game)
    game.systems.append(game.spells.tick)
