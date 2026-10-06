"""The spells' own formulas (SpellDataResource.mSpellCalculations, the GameCalculation trees the client uses for its
tooltips and the server for its numbers) evaluated for a caster's stats, rank and level.

Calculation names: the keys are FNV-1a hashes of names like "TotalDamage"; the names come from the @Name@ tokens of
the English string table (Localized/Global.en_US.wad.client). Data values (mDataValues) are referred to by the hash
of their mName; effect amounts by their 1-based index.

Checked on the replay: Darius Q, rank 1, AD 77.4 -> 50 + 1.0 x 77.4 = 127.4 = the 263 of 113.76 s on a minion.

  spell_calc.py <champion> [spell]     every calculation of the champion's spells, named, evaluated at rank 1
  spell_calc.py census                 which part types all champions' spells use, and how many are evaluable
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import bin_tree as BT  # noqa: E402

STRINGS = os.path.join(ROOT, 'data', 'exe133', 'stringtable_en_us.bin')
_names = None


def fnv(s):
    h = 0x811c9dc5
    for c in s.lower().encode():
        h = ((h ^ c) * 0x01000193) & 0xffffffff
    return h


def calc_names():
    """{'{hash}': name} for the @Name@ tokens of the string table"""
    global _names
    if _names is None:
        d = open(STRINGS, 'rb').read()
        _names = {}
        for t in set(re.findall(rb'@([A-Za-z0-9_]+)', d)):
            n = t.decode()
            _names[f'{{{fnv(n):08x}}}'] = n
    return _names


class Stats:
    """the caster's stats: AD / AP / armor..., each as (base, bonus)"""

    def __init__(self, **kw):
        self.v = kw

    def get(self, stat, formula):
        # mStat: 0 AP, 1 armor, 2 AD, 3 attack speed, 4 MR, 5 move speed, 6 crit, 7 crit damage, 8 ?,
        # 11 max health, 12 health (assumed from use; 2 = AD checked: Darius Q)
        # mStatFormula: 0 total, 1 base, 2 bonus (Darius passive: bonus AD)
        names = {0: 'ap', 1: 'armor', 2: 'ad', 3: 'as', 4: 'mr', 5: 'ms', 6: 'crit', 7: 'critdmg', 11: 'hp',
                 12: 'hpcur'}
        if stat == 'mana':
            base, bonus = self.v.get('mana', (0.0, 0.0))
            return base + bonus
        base, bonus = self.v.get(names.get(stat, f'stat{stat}'), (0.0, 0.0))
        return {0: base + bonus, 1: base, 2: bonus}.get(formula, base + bonus)


class Unknown(Exception):
    pass


def evaluate(spell, calc_key, rank=1, level=1, stats=None, _depth=0):
    """value of the calculation `calc_key` ('{hash}') of a SpellObject value; raises Unknown for a part type that is
    not handled (so coverage can be counted)"""
    stats = stats or Stats()
    sd = spell['mSpell']
    calcs = sd.get('mSpellCalculations', {})
    effects = sd.get('mEffectAmount', [])
    dvals = {f'{{{fnv(dv["mName"]):08x}}}': dv.get('mValues', [0] * 7) for dv in sd.get('mDataValues', [])
             if isinstance(dv, dict) and 'mName' in dv}

    def dv(ref):
        """a data value by reference: bainfo writes it as {hash} or, when it knows the name, as the name"""
        if not isinstance(ref, str):
            return []
        return dvals.get(ref if ref.startswith('{') else f'{{{fnv(ref):08x}}}', [])

    def at(lst):
        if not lst:
            return 0.0
        return float(lst[min(rank, len(lst) - 1)])

    def part(p):
        t = p.get('_type')
        if t == 'NumberCalculationPart':
            return float(p.get('mNumber', 0))
        if t == 'EffectValueCalculationPart':
            i = p.get('mEffectIndex', 1) - 1
            return at(effects[i].get('value', [])) if i < len(effects) else 0.0
        if t == 'NamedDataValueCalculationPart':
            return at(dv(p.get('mDataValue')))
        if t == 'StatByCoefficientCalculationPart':
            return stats.get(p.get('mStat', 0), p.get('mStatFormula', 0)) * float(p.get('mCoefficient', 0))
        if t == 'StatByNamedDataValueCalculationPart':
            return stats.get(p.get('mStat', 0), p.get('mStatFormula', 0)) * at(dv(p.get('mDataValue')))
        if t == 'StatBySubPartCalculationPart':
            return stats.get(p.get('mStat', 0), p.get('mStatFormula', 0)) * part(p['mSubpart'])
        if t == 'SumOfSubPartsCalculationPart':
            return sum(part(x) for x in p.get('mSubparts', []))
        if t == 'ProductOfSubPartsCalculationPart':
            return part(p['mPart1']) * part(p['mPart2'])
        if t == 'ByCharLevelInterpolationCalculationPart':
            a, b = float(p.get('mStartValue', 0)), float(p.get('mEndValue', 0))
            return a + (b - a) * (level - 1) / 17
        if t == 'ByCharLevelBreakpointsCalculationPart':
            v = float(p.get('mLevel1Value', 0))
            per = float(p.get('mInitialBonusPerLevel', 0))
            bps = sorted((b.get('mLevel', 99), float(b.get('mBonusPerLevelAtAndAfter', 0))) for b in p.get('mBreakpoints', []))
            for lv in range(2, level + 1):
                for bl, bv in bps:
                    if lv >= bl:
                        per = bv
                v += per
            return v
        if t == 'GameCalculation':
            return calc(p)
        if t == 'CooldownMultiplierCalculationPart':
            return 100.0 / (100.0 + stats.v.get('haste', 0.0))
        if t in ('BuffCounterByNamedDataValueCalculationPart', 'BuffCounterByCoefficientCalculationPart'):
            n = stats.v.get('buff_stacks', {}).get(p.get('mBuffName'), 0)
            k = at(dv(p.get('mDataValue'))) if 'mDataValue' in p else float(p.get('mCoefficient', 0))
            return n * k
        if t == 'ClampSubPartsCalculationPart':
            v = sum(part(x) for x in p.get('mSubparts', []))
            lo, hi = p.get('mFloor'), p.get('mCeiling')
            if isinstance(lo, (int, float)):
                v = max(v, lo)
            if isinstance(hi, (int, float)):
                v = min(v, hi)
            return v
        if t == 'AbilityResourceByCoefficientCalculationPart':
            return stats.get('mana', 0) * float(p.get('mCoefficient', 0))
        if t == 'ByCharLevelFormulaCalculationPart':
            vals = p.get('mValues', [])
            return float(vals[min(level, len(vals) - 1)]) if vals else 0.0
        raise Unknown(t)

    def calc(c):
        t = c.get('_type')
        if t == 'GameCalculationModified':
            inner = c['mModifiedGameCalculation']
            base = calc(inner) if isinstance(inner, dict) else evaluate(spell, inner, rank, level, stats, _depth + 1)
            return part(c['mMultiplier']) * base
        if t == 'GameCalculation':
            v = sum(part(x) for x in c.get('mFormulaParts', []))
            if 'mMultiplier' in c:
                v *= part(c['mMultiplier'])
            return v
        if t == 'GameCalculationConditional':
            inner = c['mDefaultGameCalculation']
            return calc(inner) if isinstance(inner, dict) else evaluate(spell, inner, rank, level, stats, _depth + 1)
        raise Unknown(t)

    if _depth > 8 or calc_key not in calcs:
        raise Unknown(f'calculation {calc_key}')
    return calc(calcs[calc_key])


def named_calcs(spell):
    names = calc_names()
    return {names.get(k, k): k for k in spell['mSpell'].get('mSpellCalculations', {})}


def census():
    import collections
    champs = sorted(f[:-11] for f in os.listdir(BT.GAME) if f.endswith('.wad.client') and '.' not in f[:-11])
    total = ok = 0
    unknown = collections.Counter()
    damage_named = 0
    for c in champs:
        try:
            spells = BT.champion_spells(c)
            rec = BT.character_record(c) or {}
        except Exception:
            continue
        main = [n.split('/')[-1] for n in rec.get('spellNames', [])][:4]
        for s in main:
            sp = spells.get(s)
            if not sp or 'mSpell' not in sp:
                continue
            calcs = sp['mSpell'].get('mSpellCalculations', {})
            if not calcs:
                continue
            total += 1
            good = True
            for k in calcs:
                try:
                    evaluate(sp, k, 1, 1, Stats(ad=(60.0, 10.0), ap=(0.0, 20.0)))
                except Unknown as e:
                    unknown[str(e)] += 1
                    good = False
                except Exception as e:
                    unknown[type(e).__name__] += 1
                    good = False
            ok += good
            if any('damage' in n.lower() for n in named_calcs(sp)):
                damage_named += 1
    print(f'{total} spells with calculations; {ok} fully evaluable; {damage_named} with a calculation named *Damage*')
    print('not handled:', unknown.most_common(20))


if __name__ == '__main__':
    if sys.argv[1] == 'census':
        census()
    else:
        sp = BT.champion_spells(sys.argv[1])
        for name, s in sp.items():
            if len(sys.argv) > 2 and name != sys.argv[2]:
                continue
            if 'mSpell' not in s or not s['mSpell'].get('mSpellCalculations'):
                continue
            out = []
            for n, k in named_calcs(s).items():
                try:
                    out.append(f'{n}={evaluate(s, k, 1, 1, Stats(ad=(64.0, 13.4))):.2f}')
                except Unknown as e:
                    out.append(f'{n}=?({e})')
            print(name, ', '.join(out))
