"""Generic spells for every champion, from the game's own data: where a cast lands, whom it hits, how much damage of
which type, and when. Used by lnp_server.py for spells that have no replay-measured template.

What comes from the data (SpellDataResource): targeting (mTargetingTypeData), castRange, castRadius, mLineWidth,
castConeAngle / castConeDistance, missileSpeed, the cast times (spell_info.cast_times, checked on the replay), the
damage (spell_calc.py, the spell's own mSpellCalculations; Darius Q checked exactly on the replay).
What is approximated (no script for the spell is shipped with the client): which calculation is THE damage (the one
named TotalDamage / Damage / ...Damage), the damage type (magic when the calculation uses ability power, else
physical), that a missile stops at the first enemy, and hit timing = windup + travel at missileSpeed.

  spell_engine.py <champion>      the shape and the damage of its Q/W/E/R at rank 1, level 1
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bin_tree as BT  # noqa: E402
import spell_calc as SC  # noqa: E402
import spell_info as SI  # noqa: E402


def main_spells(champion):
    rec = BT.character_record(champion) or {}
    return [n.split('/')[-1] for n in rec.get('spellNames', [])][:4]


def _at(lst, rank):
    if isinstance(lst, list) and lst:
        return float(lst[min(rank, len(lst) - 1)])
    if isinstance(lst, (int, float)):
        return float(lst)
    return 0.0


def shape(champion, spell, rank=1):
    sp = BT.champion_spells(champion).get(spell, {})
    sd = sp.get('mSpell', {})
    tt = sd.get('mTargetingTypeData')
    targeting = tt if isinstance(tt, str) else (tt or {}).get('_type', 'Target') if isinstance(tt, dict) else 'Target'
    rng = _at(sd.get('castRangeDisplayOverride'), rank) or _at(sd.get('castRange'), rank) or 0.0
    return {
        'spell': spell,
        'targeting': targeting or 'Target',
        'range': rng,
        'radius': _at(sd.get('castRadius'), rank) or 0.0,
        'width': float(sd.get('mLineWidth', 0) or 0),
        'cone_angle': float(sd.get('castConeAngle', 0) or 0),
        'cone_distance': float(sd.get('castConeDistance', 0) or 0),
        'missile_speed': float(sd.get('missileSpeed', 0) or 0),
        'scripted': bool(int(sd.get('flags', 0) or 0) & 4),
    }


def damage_calc(champion, spell):
    """the calculation taken as the spell's damage: TotalDamage, Damage, then the first *Damage* name"""
    sp = BT.champion_spells(champion).get(spell)
    if not sp or 'mSpell' not in sp:
        return None, None
    named = SC.named_calcs(sp)
    for want in ('TotalDamage', 'Damage', 'TotalDamageTooltip', 'DamageTooltip'):
        if want in named:
            return sp, named[want]
    for n, k in named.items():
        if 'damage' in n.lower() and 'reduction' not in n.lower() and 'bonus' not in n.lower():
            return sp, k
    return sp, None


def _uses_stat(node, stat):
    if isinstance(node, dict):
        if node.get('_type', '').startswith('StatBy') and node.get('mStat', 0) == stat:
            return True
        return any(_uses_stat(v, stat) for v in node.values())
    if isinstance(node, list):
        return any(_uses_stat(v, stat) for v in node)
    return False


def _uses_ap(node):
    if isinstance(node, dict):
        if node.get('_type', '').startswith('StatBy') and node.get('mStat', 0) == 0:   # a missing mStat = 0 = AP
            return True
        return any(_uses_ap(v) for v in node.values())
    if isinstance(node, list):
        return any(_uses_ap(v) for v in node)
    return False


def damage(champion, spell, rank, level, stats):
    """(amount before mitigation, type 0 physical / 1 magic, calculation name) or None"""
    sp, key = damage_calc(champion, spell)
    if not key:
        return None
    try:
        v = SC.evaluate(sp, key, rank, level, stats)
    except SC.Unknown:
        return None
    calc = sp['mSpell']['mSpellCalculations'][key]
    # physical when the formula scales with AD (stat 2), else magic when it scales with AP [approximation: the type is
    # not in the data; replay: Darius physical, Azir magic]
    kind = 0 if _uses_stat(calc, 2) else 1 if _uses_ap(calc) else 0
    return v, kind, SC.calc_names().get(key, key)


def _dist_point_segment(p, a, b):
    ax, az = a
    bx, bz = b
    px, pz = p
    dx, dz = bx - ax, bz - az
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz)), t


def hits(sh, caster, aim, units):
    """units: [(net, (x, z), radius)] that can be hit; -> [(net, travel distance)] hit by the cast"""
    t = sh['targeting']
    cx, cz = caster
    ax, az = aim
    out = []
    if t in ('Self', 'SelfAoe'):
        r = max(sh['radius'], sh['range'])     # Garen E: castRadius 35, castRangeDisplayOverride 325 (its real area)
        for n, (x, z), ur in units:
            if math.hypot(x - cx, z - cz) <= r + ur:
                out.append((n, 0.0))
        return out if t == 'SelfAoe' else out
    if t in ('Location', 'LocationClamped') and sh['width'] > 0 and sh['missile_speed'] > 0:
        t = 'direction'           # a missile with a width flies in a line towards the point (Lux Q) [approximation]
    if t in ('direction', 'DragDirection', 'WallDetection'):
        d = math.hypot(ax - cx, az - cz) or 1.0
        L = sh['range'] or d
        end = (cx + (ax - cx) / d * L, cz + (az - cz) / d * L)
        w = (sh['width'] or 60.0)
        cand = []
        for n, (x, z), ur in units:
            dist, f = _dist_point_segment((x, z), (cx, cz), end)
            if dist <= w + ur:
                cand.append((f * L, n))
        cand.sort()
        return [(n, along) for along, n in cand[:1]]          # a missile stops at the first enemy [approximation]
    if t in ('Location', 'LocationClamped', 'Area', 'AreaClamped', 'TerrainLocation'):
        d = math.hypot(ax - cx, az - cz)
        if sh['range'] and d > sh['range']:
            f = sh['range'] / d
            ax, az = cx + (ax - cx) * f, cz + (az - cz) * f
        r = sh['radius'] or 100.0
        for n, (x, z), ur in units:
            if math.hypot(x - ax, z - az) <= r + ur:
                out.append((n, math.hypot(ax - cx, az - cz)))
        return out
    if t in ('direction', 'DragDirection', 'WallDetection'):
        d = math.hypot(ax - cx, az - cz) or 1.0
        L = sh['range'] or d
        end = (cx + (ax - cx) / d * L, cz + (az - cz) / d * L)
        w = (sh['width'] or 60.0)
        cand = []
        for n, (x, z), ur in units:
            dist, f = _dist_point_segment((x, z), (cx, cz), end)
            if dist <= w + ur:
                cand.append((f * L, n))
        cand.sort()
        return [(n, along) for along, n in cand[:1]]          # a missile stops at the first enemy [approximation]
    if t == 'Cone':
        dirx, dirz = ax - cx, az - cz
        dn = math.hypot(dirx, dirz) or 1.0
        half = math.radians((sh['cone_angle'] or 45.0) / 2)
        L = sh['cone_distance'] if sh['cone_distance'] > 100 else (sh['range'] or 500.0)
        for n, (x, z), ur in units:
            vx, vz = x - cx, z - cz
            vd = math.hypot(vx, vz)
            if vd <= L + ur and vd > 0 and math.acos(max(-1, min(1, (vx * dirx + vz * dirz) / (vd * dn)))) <= half:
                out.append((n, vd))
        return out
    # Target / TargetOrLocation / none: the enemy closest to the aimed point, within range
    best = None
    for n, (x, z), ur in units:
        d_aim = math.hypot(x - ax, z - az)
        if d_aim <= 150 + ur and math.hypot(x - cx, z - cz) <= (sh['range'] or 600.0) + ur:
            if best is None or d_aim < best[0]:
                best = (d_aim, n, math.hypot(x - cx, z - cz))
    return [(best[1], best[2])] if best else []


def hit_delay(champion, sh, travel):
    windup, _ = SI.cast_times(champion, sh['spell'])
    if sh['missile_speed'] > 0 and sh['targeting'] not in ('Self', 'SelfAoe'):
        return windup + travel / sh['missile_speed']
    return windup


if __name__ == '__main__':
    c = sys.argv[1]
    for s in main_spells(c):
        sh = shape(c, s)
        dm = damage(c, s, 1, 1, SC.Stats(ad=(60.0, 0.0), ap=(0.0, 0.0)))
        print(s, sh, dm)
