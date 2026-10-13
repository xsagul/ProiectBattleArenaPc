"""The map's own units: lane minions, turrets, jungle monsters.

Lane minions [measured on the live recording unless marked]:
  - a minion walks its lane's waypoints (the map's MinionPath_*), one straight path to the next waypoint at a time:
    the server sends a movement entry when the path changes, not while it walks
  - it looks around four times a second [a: LeagueSandbox's lane minion does the same]; an enemy inside its
    acquisition range (the record's firstAcquisitionRange / acquisitionRange) becomes its target: the nearest enemy
    minion, else a structure that can be attacked, else a champion [a: the order of LoL's known priority list]
  - it walks to a place of its own next to the target and attacks: period, windup and missile speed are the
    record's (melee 0.8 s, caster 1.5 s, siege 1.0 s between attacks)
  - a champion that damages an enemy champion near minions draws those minions onto itself for a short while
  - a champion that damages a minion is "called for help" on by that minion's side [LoL's priority list: an enemy
    champion attacking an allied minion comes before the nearest enemy minion]; it does not pull a minion off the
    target it fights, only one choosing a new target [m: 12 replays - 157 of 252 minion attack orders at champions
    in 150 s follow that champion's hit on a minion by 0 - 1.4 s; the minions stay on it about one attack (~1 s)]
Turrets: the target stays until it dies or leaves; minions before champions (the record's towerTargetingPriorityBoost),
a champion that damages an allied champion in the turret's reach becomes the target; the shot is 0.266 s after the
attack packet [m], the missile flies at 1200.
"""
import math
import os

from . import packets as P
from .units import dist, NEUTRAL, FRAME

THINK = 2.0 * FRAME              # [m: the replays - a minion following a champion repeats its 515 every two frames] its AI runs every 2 frames
HELP_TIME = 2.5
MINION_CALL = 1.5                # [m] a champion's hit on a minion draws that side's minions choosing a target this long
MINION_CALL_HOLD = 1.0           # [m] and they stay on it about one attack
HERO_ACQUIRE = 550.0
LEASH = 250.0
TURRET_WINDUP = 0.266
# [Riot's Leashy.lua of the 13.3 client, read from its bytecode] a camp monster's leash:
#   TimerFrustrationSearch (every 0.05 s; 0.6 s after a frustration): frustrated when it has no target, when its
#     target is more than 650 + OUTER_RANGE_BOUND (900) walking from the camp (unless retreating), or when it is itself
#     more than 900 from the camp -> IncreaseFrustration: the counter + 1 (and a JungleFrustration stack); above
#     LEASH_COUNTER_THRESHOLD (6) it retreats: walks home ghosted, regenerating (OutOfCombatRegen), state AI_RETREAT
#   TimerReturningHome: within 25 of the camp and stopped -> the counter back to 0, the state back to attack
#   OnTakeDamage while retreating (RespondToAggression -> LeashedCallForHelp): only with the counter below the
#     threshold and the attacker within 650 of the camp, or the monster within INNER_RANGE_BEFORE_CAMP_RELEASES (700)
#     of it and the attacker within ATTACKER_RANGE_BEFORE_RELEASH (1150)
# [m: replay 4012247271 - Gromp chased Kindred 2.5 s ~1100 from its camp, then attacked again; the minis of a
# Razorbeak camp hit by Lee Sin's Q from 1200 chased him]
MONSTER_LEASH = 1150.0
LEASH_CAMP = 650.0 + 250.0
FRUSTRATION_LIMIT, FRUSTRATION_SEARCH, FRUSTRATION_DELAY = 6, 0.05, 0.6
RESPOND_RANGE, INNER_RANGE = 650.0, 700.0
AGGRESSOR_MEMORY = 4.0


# ------------------------------------------------------------------------------------------------ lane minions
def minion_values(g, m):
    """the replicated values of a new lane minion: the real server's full set (three blocks within 0.2 s of the
    spawn; forms16.json keeps them) with this minion's own numbers"""
    blocks = g.pk.forms['minion']['blocks']
    v = {}
    for blk in blocks.get(str(m.mtype)) or blocks['6' if m.mtype == 7 else '4']:
        if blk['delay'] < 1.0:
            v.update(blk['values'])
    v.update({'mHP': m.hp, 'mMaxHP': m.max_hp, 'mBaseAttackDamage': m.base_ad, 'mArmor': m.armor, 'mSpellBlock': m.mr,
              'mAttackRange': m.range, 'mMoveSpeed': m.speed, 'mCritDamageMultiplier': 2.0, 'mIsTargetable': 1,
              'mIsTargetableToTeamFlags': 4, 'mSAR': 100.0, 'mMaxSAR': 100.0})
    return v


def lane_resume(g, m):
    """back onto the lane: towards the next waypoint that is still ahead of where it stands"""
    pts = m.lane_points
    i = m.lane_i
    while i < len(pts) - 1:
        a, b = pts[i], pts[i + 1]
        if (m.pos[0] - a[0]) * (b[0] - a[0]) + (m.pos[1] - a[1]) * (b[1] - a[1]) > 0 or dist(m.pos, a) < 30.0:
            i += 1                                   # that waypoint is behind it already
        else:
            break
    m.lane_i = i
    if dist(m.pos, pts[i]) > 5.0:
        walk(g, m, pts[i])


def minion_arrived(g, m):
    if m.target is None:
        if dist(m.pos, m.lane_points[m.lane_i]) < 30.0 and m.lane_i < len(m.lane_points) - 1:
            m.lane_i += 1
        lane_resume(g, m)


def walk(g, u, goal):
    """straight when nothing is in the way, else around walls"""
    if g.nav.line_clear(u.pos, goal):
        u.go([goal])
    else:
        u.path_to(goal)


def minion_hit(g, src, victim):
    """a champion damaged a lane minion: a call for help on it, for the victim's side"""
    calls = g.__dict__.setdefault('minion_calls', {})
    calls.setdefault(victim.team, {})[src.net] = g.t


def called(g, m):
    """the nearest enemy champion that hit one of m's allied minions lately and stands within its acquisition range"""
    calls = getattr(g, 'minion_calls', {}).get(m.team) or {}
    acq = m.base.get('acquire') or 600.0
    best = None
    for net, t in calls.items():
        if g.t - t > MINION_CALL:
            continue
        h = g.units.get(net)
        if h is None or not h.alive or not h.targetable or not g.seen_by(m.team, h):
            continue
        d = dist(h.pos, m.pos)
        if d <= acq and (best is None or d < best[0]):
            best = (d, h)
    return best[1] if best else None


def acquire(g, m):
    acq = m.base.get('acquire') or 600.0
    best = None
    px, pz = m.pos
    for o in g.units.values():
        if o.team == m.team or o.team == NEUTRAL or not o.alive or not o.targetable:
            continue
        d = math.hypot(o.pos[0] - px, o.pos[1] - pz)
        if o.is_hero:
            if d > HERO_ACQUIRE:
                continue
            rank = 2
        elif o.is_structure:
            if d > acq + o.radius:
                continue
            rank = 1
        else:
            if d > acq:
                continue
            rank = 0
        if not g.seen_by(m.team, o):
            continue
        if best is None or (rank, d) < best[0]:
            best = ((rank, d), o)
    return best[1] if best else None


def free_spot(g, m, tgt):
    """a place for m to attack tgt from that no other minion of its lane stands on or walks to: on a circle around
    the target, starting on m's side and stepping to both sides"""
    dx, dz = m.pos[0] - tgt.pos[0], m.pos[1] - tgt.pos[1]
    d = math.hypot(dx, dz) or 1.0
    r = min(d, m.reach(tgt) - 15.0)
    base = math.atan2(dz, dx)
    step = 2 * math.asin(min(1.0, m.radius / max(r, m.radius)))
    others = [(o.spot if (o.spot and o.path) else o.pos) for o in g.minions
              if o is not m and o.alive and o.lane == m.lane and dist(o.pos, tgt.pos) < r + 300]
    for k in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
        a = base + k * step
        p = (tgt.pos[0] + r * math.cos(a), tgt.pos[1] + r * math.sin(a))
        if all(dist(p, q) > 1.7 * m.radius for q in others) and not g.nav.is_blocked(*p):
            return p
    return (tgt.pos[0] + r * math.cos(base), tgt.pos[1] + r * math.sin(base))


def minion_tick(g, m, t):
    state = m.attack_tick(t)
    if state == 'windup' or t < m.next_think:
        return
    m.next_think = t + THINK
    tgt = g.units.get(m.target) if m.target else None
    if tgt is not None and (not m.can_target(tgt) or dist(m.pos, tgt.pos) > (m.base.get('acquire') or 600.0) + LEASH + tgt.radius):
        m.target, tgt = None, None
    forced = getattr(m, 'help_until', 0.0) > t
    if tgt is None:
        new = called(g, m)
        if new is not None:
            tgt = new
            m.target, m.spot = tgt.net, None
            m.help_until = t + MINION_CALL_HOLD
            forced = True
    if tgt is None or (not forced and not tgt.is_structure and tgt.kind != 'minion'):
        new = acquire(g, m)
        if new is not None and (tgt is None or new.kind == 'minion'):
            tgt = new
            m.target, m.spot = tgt.net, None
    if tgt is None:
        m.spot = None
        if not m.path:
            lane_resume(g, m)
        return
    if m.in_reach(tgt):
        return                                           # attack_tick stands and attacks
    if m.spot is None or dist(m.spot, tgt.pos) > m.reach(tgt) + 10.0:
        m.spot = free_spot(g, m, tgt)
    if not m.path or dist(m.path[-1], m.spot) > 20.0:
        walk(g, m, m.spot)


def call_for_help(g, victim, attacker):
    """an enemy champion has damaged a champion: the victim's minions and turret near turn on the attacker"""
    t = g.t
    for m in g.minions:
        if m.team == victim.team and m.alive and dist(m.pos, attacker.pos) <= (m.base.get('acquire') or 600.0) and \
                dist(m.pos, victim.pos) <= 1000.0 and getattr(m, 'help_until', 0.0) < t:
            m.help_until = t + HELP_TIME
            if m.windup_end is None:
                m.target, m.spot = attacker.net, None
    for tu in g.turrets:
        if tu.team == victim.team and tu.alive and tu.in_reach(attacker) and tu.target != attacker.net:
            cur = g.units.get(tu.target)
            if cur is None or not cur.is_hero:
                set_turret_target(g, tu, attacker)


# ------------------------------------------------------------------------------------------------ turrets
def set_turret_target(g, tu, tgt):
    """266 [m]: the unit a turret has locked on (0 = none); the client draws the warning from it"""
    tu.target = tgt.net if tgt is not None else None
    tu.heat = 0
    g.q.append((1, 266, tu.net, g.pk.enc(266, {'+0x10': P.u32(tgt.net if tgt is not None else 0)})))


def turret_choose(g, tu):
    best = None
    for o in g.units.values():
        if o.team == tu.team or o.team == NEUTRAL or not o.alive or not o.targetable or o.is_structure:
            continue
        if not tu.in_reach(o) or not g.seen_by(tu.team, o):
            continue
        if tu.tier == 'fountain' and not o.is_hero:
            continue
        d = dist(tu.pos, o.pos)
        rank = (1, 0.0, d) if o.is_hero else (0, -float(o.base.get('tower_priority', 0.0)), d)
        if best is None or rank < best[0]:
            best = (rank, o)
    return best[1] if best else None


def turret_tick(g, tu, t):
    state = tu.attack_tick(t)
    if state == 'windup' or t < tu.next_think:
        return
    tu.next_think = t + 0.1
    tgt = g.units.get(tu.target) if tu.target else None
    if tu.target and (tgt is None or not tu.can_target(tgt) or not tu.in_reach(tgt)):
        set_turret_target(g, tu, None)
        tgt = None
    if tgt is None:
        tgt = turret_choose(g, tu)
        if tgt is not None:
            set_turret_target(g, tu, tgt)
            tu.attack_ready = max(tu.attack_ready, t + 0.25)


# ------------------------------------------------------------------------------------------------ jungle monsters
LUA_AI = os.environ.get('BA_LUA_AI') == '1'     # camp monsters run Riot's own Leashy.lua (core/luaapi.py)


def lua_host(g, mo):
    h = getattr(mo, 'lua', None)
    if h is None and mo.alive:
        from .luaapi import AIHost
        h = mo.lua = AIHost(g, mo, 'leashy')
        h.on_state = lambda old, new, mo=mo: lua_state_changed(g, mo, old, new)
        h.on_roam = lambda old, new, mo=mo: lua_roam_changed(g, mo, old, new)
    return h


def lua_state_changed(g, mo, old, new):
    """the engine's own 586 (the camp's leash state) as the script's state changes [m: 5 on engaging, 8 giving up,
    9 + 3 home, 1 1.8 s later; which engine change sends which is our reading]"""
    from .luaapi import CONSTANTS as C
    if new == C['AI_RETREAT'] and getattr(mo, 'leash', 1) != 8:
        mo.leash = 8
        g.q += g.pk.leash_state(mo.net, 8)
    elif new == C['AI_ATTACK'] and old == C['AI_RETREAT']:
        mo.leash = 1
        mo.reset_heal_from = None
        g.q += g.pk.leash_state(mo.net, 9) + g.pk.leash_state(mo.net, 3)
        g.at(g.t + 1.8, lambda t, mo=mo: mo.alive and getattr(mo, 'leash', 1) == 1 and g.q.extend(g.pk.leash_state(mo.net, 1)))


def lua_roam_changed(g, mo, old, new):
    """[m: 586 state 5, twice, in the frame of the hit that engages the camp] the script turns the monster hostile"""
    if new == 1 and getattr(mo, 'leash', 1) != 5:            # Leashy's HOSTILE
        mo.leash = 5
        mo.reset_heal_from = None
        g.q += g.pk.leash_state(mo.net, 5) * 2


def lua_monster_tick(g, mo, t):
    h = lua_host(g, mo)
    from .luaapi import CONSTANTS as C
    h.tick(t)
    mo.attack_tick(t)
    if t >= mo.next_think:
        mo.next_think = t + THINK
        if getattr(mo, 'leash', 1) == 8 and mo.hp < mo.max_hp:
            if getattr(mo, 'reset_heal_from', None) is None:
                mo.reset_heal_from = t
            else:
                monster_reset_heal(g, mo)        # the engine's regeneration of a retreating monster (measured)


def monster_hit(g, mo, src):
    """a monster that is hit turns on whoever hit it, and so does its camp"""
    if src is None or not src.alive:
        return
    if LUA_AI:
        for o in g.monsters:
            if o.alive and o.camp == mo.camp:
                h = lua_host(g, o)
                if h is not None:
                    h.call('LeashedCallForHelp', mo, src)
        return
    for o in g.monsters:
        if o.alive and o.camp == mo.camp and (o.target is None or o is mo):
            if getattr(o, 'leash', 1) == 8:
                # retreating: it answers only while its frustration is below the limit and the attacker is near the
                # camp (Leashy.lua's LeashedCallForHelp)
                far = dist(src.pos, o.home)
                if getattr(o, 'frustration', 0) >= FRUSTRATION_LIMIT or not (
                        far <= RESPOND_RANGE or (dist(o.pos, o.home) <= INNER_RANGE and far <= MONSTER_LEASH)):
                    continue
            if o.target is None:
                o.target = src.net
                o.aggro_at = g.t
                o.reset_heal_from = None
                if getattr(o, 'leash', 1) != 5:
                    o.leash = 5
                    g.q += g.pk.leash_state(o.net, 5) * 2


def monster_tick(g, mo, t):
    state = mo.attack_tick(t)
    if state == 'windup' or t < mo.next_think:
        return
    mo.next_think = t + THINK
    tgt = g.units.get(mo.target) if mo.target else None
    if tgt is not None and not tgt.alive:
        tgt = None
    if tgt is None and getattr(mo, 'leash', 1) == 5:
        # its target is lost: the nearest champion that hit the camp, within 900 of it (Leashy.lua's AttackerSweep,
        # FindNearestAggressor) [a: 'hit the camp' = in the last AGGRESSOR_MEMORY s]
        hits = {}
        for o in g.monsters:
            if o.camp == mo.camp:
                for n, when in o.last_hit_by.items():
                    hits[n] = max(hits.get(n, 0.0), when)
        near = [(dist(h.pos, mo.pos), h) for h in g.heroes if h.alive and t - hits.get(h.net, -99.0) <= AGGRESSOR_MEMORY
                and dist(h.pos, mo.home) <= LEASH_CAMP]
        if near:
            tgt = min(near, key=lambda x: x[0])[1]
            mo.target = tgt.net
    if getattr(mo, 'leash', 1) == 5 and t >= getattr(mo, 'frustration_next', 0.0):
        frustrated = tgt is None or dist(tgt.pos, mo.home) > LEASH_CAMP or dist(mo.pos, mo.home) > LEASH_CAMP
        if frustrated:
            mo.frustration = getattr(mo, 'frustration', 0) + 1
            mo.frustration_next = t + FRUSTRATION_DELAY
        else:
            mo.frustration_next = t + FRUSTRATION_SEARCH
        if tgt is None or getattr(mo, 'frustration', 0) > FRUSTRATION_LIMIT:
            mo.target, tgt = None, None
            mo.leash = 8                                 # it retreats [m: 586 state 8, then 9 / 3 / 1 back home [a]]
            g.q += g.pk.leash_state(mo.net, 8)
    elif tgt is None:
        mo.target = None
    if tgt is None:
        released = getattr(mo, 'leash', 1) == 8
        if dist(mo.pos, mo.home) > 25.0 and not mo.path:
            walk_to(g, mo, mo.home)
        if mo.hp < mo.max_hp and released and getattr(mo, 'reset_heal_from', None) is None:
            mo.reset_heal_from = t                       # the heals begin on the next think
        elif mo.hp < mo.max_hp and released:
            monster_reset_heal(g, mo)                    # a monster that gave up heals on its way home and there
        elif released and dist(mo.pos, mo.home) <= 25.0:
            mo.leash = 1                                 # home and whole again
            mo.reset_heal_from = None
            mo.frustration = 0
            g.q += g.pk.leash_state(mo.net, 9) + g.pk.leash_state(mo.net, 3)
            g.at(g.t + 1.8, lambda t, mo=mo: mo.alive and getattr(mo, 'leash', 1) == 1 and g.q.extend(g.pk.leash_state(mo.net, 1)))
        return
    if not mo.in_reach(tgt):
        if not mo.path or dist(mo.path[-1], tgt.pos) > 60.0:
            walk_to(g, mo, tgt.pos)


# [m: 4 reset camps of replay 4012247271, 700 heal events] a monster that gave up its target (586 state 8) heals every
# second frame, from the second frame after, 10 % of its health a second (0.1 x 2 / 30 of it each time; the last one
# what is missing), each with its 699 heal event (flag 6, no name), until whole
RESET_HEAL = 0.1 * 2.0 / 30.0


def monster_reset_heal(g, mo):
    amount = min(mo.max_hp - mo.hp, mo.max_hp * RESET_HEAL)
    if amount <= 0:
        return
    mo.set_hp(mo.hp + amount)
    g.q += g.pk.heal_event(mo.net, mo.net, amount, cause=0, name=0, flag=6, tail=bytes.fromhex('ffffffff56077be8'))


def walk_to(g, u, place):
    """straight when nothing is in the way, around the walls otherwise"""
    if g.nav.line_clear(u.pos, place):
        u.go([place])
    else:
        u.path_to(place)


def tick(g, t):
    for m in g.minions:
        if m.alive:
            minion_tick(g, m, t)
    for tu in g.turrets:
        if tu.alive:
            turret_tick(g, tu, t)
    for mo in g.monsters:
        if mo.alive:
            if LUA_AI:
                lua_monster_tick(g, mo, t)
            else:
                monster_tick(g, mo, t)
