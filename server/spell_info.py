"""A champion's spell data from the game files (lol13.3), through our bainfo tool (`bainfo spells`, whose "ranks"
line prints every rank): cast time, cooldown and mana per rank, the animation the spell plays, the spell's data values per rank (mDataValues,
e.g. GarenE Duration).

  spell_info.py <Champion>          every spell of the champion
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
BAINFO = os.path.join(ROOT, 'tools', 'bin', 'bainfo.exe')
GAME = os.path.join(ROOT, 'game16' if os.environ.get('BA_PATCH') == '1620' else 'game', 'DATA', 'FINAL', 'Champions')
_cache = {}


def elf(name):
    """the 32-bit ELF hash of a spell name, lower case: how packets 49 and 16 name a spell"""
    h = 0
    for c in name.lower().encode():
        h = (h << 4) + c
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


def spells(champion):
    if champion in _cache:
        return _cache[champion]
    wad = os.path.join(GAME, f'{champion}.wad.client')
    out = subprocess.run([BAINFO, 'spells', wad, champion, 'all'], capture_output=True, text=True).stdout
    res = {}
    cur = None
    for line in out.splitlines():
        m = re.match(r'^(\S+): (\S+), animation (\S*), cast time ([\d.]+) s', line)
        if m:
            cur = {'targeting': m.group(2), 'animation': m.group(3), 'cast_time': float(m.group(4))}
            res[m.group(1)] = cur
            continue
        m = re.match(r'^\s+cooldown [\d.]+\.\.[\d.]+, mana [\d.]+\.\.[\d.]+, range ([\d.]+)', line)
        if m and cur is not None:
            cur['range'] = float(m.group(1))
        m = re.match(r'^\s+ranks cooldown ([\d. ]+) mana ([\d. ]+)$', line)
        if m and cur is not None:
            cur['cooldown'] = [float(x) for x in m.group(1).split()]   # index 0 = rank 1
            cur['mana'] = [float(x) for x in m.group(2).split()]
            continue
        m = re.match(r'^  (\w+)\s+(-?[\d.]+(?: -?[\d.e+-]+)*)$', line)
        if m and cur is not None:
            cur.setdefault('values', {})[m.group(1)] = [float(x) for x in m.group(2).split()]   # index 0 = rank 1
    _cache[champion] = res
    return res


def at_level(values, level):
    """the value of a spell's rank (1-based), from the game file's own per-rank list"""
    return values[min(max(level, 1), len(values)) - 1]

_raw = {}


def raw_fields(champion):
    """{mScriptName: {field: scalar text}} of every SpellObject of the champion's bin (bainfo bin dump): the fields
    `bainfo spells` does not print (mCastTime, delayCastOffsetPercent, delayTotalTimePercent, castFrame, ...)"""
    if champion in _raw:
        return _raw[champion]
    wad = os.path.join(GAME, f'{champion}.wad.client')
    out = subprocess.run([BAINFO, 'bin', wad, f'data/characters/{champion.lower()}/{champion.lower()}.bin', '',
                          os.path.join(ROOT, 'data', 'hashes')], capture_output=True, text=True).stdout
    res, cur = {}, None
    for line in out.splitlines():
        if re.match(r'^\S', line):
            cur = None
        m = re.match(r'^  mScriptName: "(\w+)"', line)
        if m:
            cur = res.setdefault(m.group(1), {})
            continue
        m = re.match(r'^    (\w+): ([^\[{].*)$', line)
        if m and cur is not None:
            cur.setdefault(m.group(1), m.group(2).strip('"'))
    _raw[champion] = res
    return res


def cast_times(champion, spell):
    """(windup, total) the server writes in 49 (+0xc+0x24, +0xc+0x58): mCastTime, else 0.5 * (1 +
    delayCastOffsetPercent); 2.0 * (1 + delayTotalTimePercent) -- checked against every cast of the 13.3 replay
    (`spell_info.py check`)"""
    f = raw_fields(champion).get(spell, {})
    windup = float(f['mCastTime']) if 'mCastTime' in f else 0.5 * (1 + float(f.get('delayCastOffsetPercent', 0)))
    # never shorter than the windup (AzirW: delayTotalTimePercent -1 -> 0.25 = its windup); channels add their
    # channelDuration on top (JhinR 1 + 10 = 11 in the replay) -- not read here yet
    total = max(windup, 2.0 * (1 + float(f.get('delayTotalTimePercent', 0))))
    return windup, total

_rec = {}


def char_record(champion):
    """the champion's CharacterRecord scalars (baseHP, baseDamage, damagePerLevel, baseArmor, attackSpeed,
    attackRange, ...) and the basic attack slot's lists (basicAttack.mAttackDelayCastOffsetPercent...)"""
    if champion in _rec:
        return _rec[champion]
    wad = os.path.join(GAME, f'{champion}.wad.client')
    out = subprocess.run([BAINFO, 'bin', wad, f'data/characters/{champion.lower()}/{champion.lower()}.bin', '',
                          os.path.join(ROOT, 'data', 'hashes')], capture_output=True, text=True).stdout.splitlines()
    res, inside, sub, last = {}, False, None, None
    for i, line in enumerate(out):
        if re.match(r'^\S', line):
            if inside:
                break
            inside = '(CharacterRecord)' in line
            continue
        if not inside:
            continue
        m = re.match(r'^  (\w+): (.*)$', line)
        if m:
            sub = m.group(1) if m.group(2).startswith(('AttackSlotData', 'AbilityResourceSlotInfo')) else None
            if not m.group(2).startswith(('[', '{')) and sub is None:
                res[m.group(1)] = m.group(2).strip('"')
            elif m.group(2) == '[1]' and i + 1 < len(out):
                res[m.group(1)] = out[i + 1].strip().strip('"')     # a one-value list (overrideGameplayCollisionRadius)
            continue
        m = re.match(r'^    (\w+): ([^\[{].*)$', line)
        if m and sub:
            res[f'{sub}.{m.group(1)}'] = m.group(2).strip('"')     # primaryAbilityResource.arBase ...
            continue
        m = re.match(r'^    (\w+): \[1\]$', line)
        if m and sub and i + 1 < len(out):
            res[f'{sub}.{m.group(1)}'] = out[i + 1].strip().strip('"')
        m = re.match(r'^  (\w+): \[1\]$', line)
        if m and i + 1 < len(out):
            res[m.group(1)] = out[i + 1].strip().strip('"')     # a one-value list (overrideGameplayCollisionRadius)
    _rec[champion] = res
    return res


def attack_times(champion, attack_speed_mod=1.0):
    """(period, windup) of a basic attack: period = 1 / (attackSpeed * mod); windup = base + (period * pct - base) *
    ratio, base = pct / attackSpeed, pct = 0.3 + mAttackDelayCastOffsetPercent, ratio =
    mAttackDelayCastOffsetPercentAttackSpeedRatio -- checked on Darius's 342 replay hits (276 on the predicted 1/30 s
    server tick, 30 one tick off)"""
    r = char_record(champion)
    asp = float(r['attackSpeed'])
    period = 1 / (asp * attack_speed_mod)
    if 'basicAttack.mAttackCastTime' in r:
        windup = float(r['basicAttack.mAttackCastTime']) / attack_speed_mod
        return period, windup
    pct = 0.3 + float(r.get('basicAttack.mAttackDelayCastOffsetPercent', 0))
    ratio = float(r.get('basicAttack.mAttackDelayCastOffsetPercentAttackSpeedRatio', 1))
    base = pct / asp
    return period, base + (period * pct - base) * ratio


def basic_attack_missile_speed(champion):
    """Missile speed of a champion's basic attack: 0 for melee, > 0 for ranged (e.g. 2750 for Jinx, 2500 for Ashe)"""
    r = char_record(champion)
    atk_range = float(r.get('attackRange', 125.0))
    if atk_range <= 300.0:
        return 0.0
    raw = raw_fields(champion)
    for k in (f'{champion}BasicAttack', f'{champion}BasicAttack2', f'{champion}CritAttack', f'{champion}QAttack'):
        if k in raw and 'missileSpeed' in raw[k]:
            spd = float(raw[k]['missileSpeed'])
            if spd > 0:
                return spd
    return 2000.0


if __name__ == '__main__':
    print(json.dumps(spells(sys.argv[1]), indent=1))

