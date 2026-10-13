"""Write a champion's BuildingBlocks scripts from what the replays showed (tools/bb_infer16.py) ->
data/bb16/scripts/<Champion>/<Script>.lua, in the block-table form of Riot's own scripts (the 1.31 client's):

    SelfExecuteBuildingBlocks = { {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", ...}}, ... }

    python tools/bb_write16.py <Champion> [..]

The patterns a script is made of (each from a fact of the inference with its share; a fact below its threshold is
left out and listed in the file's header as unexplained):
  cast -> buff on itself      a buff given by the cast of a spell of the champion (share >= 0.6, held by the caster)
                              -> the spell's SelfExecute: BBSpellBuffAdd(Owner)
  cast -> buff on the target  (held by others) -> the spell's TargetExecute: BBSpellBuffAdd(Target)
  slot while it lasts         the buff's first frame puts a spell in a slot and its last puts the slot's own back
                              (share >= 0.9) -> OnBuffActivate / OnBuffDeactivate: BBSetSpell
  spent by a hit              it ends on the holder's attack hit (share >= 0.5) -> BuffOnHitUnit: the buffs that
                              begin on others in that frame (given by its end, share >= 0.5), then BBSpellBuffRemoveCurrent
  ticks                       damage named like it, every p s while it lasts -> BuffOnUpdateActions:
                              BBExecutePeriodically(p) { BBForEachUnitInTargetArea { BBApplyDamage } }
Durations: the most common one sent; types: the 435's (BuffType names). Damage numbers are not in the replays as
formulas: the engine block takes them from the spell's data (core/spells.py damage_of), named by the script.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
INFER = os.path.join(ROOT, 'data', 'bb16', 'infer')
OUT = os.path.join(ROOT, 'data', 'bb16', 'scripts')

BUFF_TYPES = ['Internal', 'Aura', 'CombatEnchancer', 'CombatDehancer', 'SpellShield', 'Stun', 'Invisibility', 'Silence',
              'Taunt', 'Berserk', 'Polymorph', 'Slow', 'Snare', 'Damage', 'Heal', 'Haste', 'SpellImmunity',
              'PhysicalImmunity', 'Invulnerability', 'AttackSpeedSlow', 'NearSight', 'Currency', 'Fear', 'Charm', 'Poison',
              'Suppression', 'Blind', 'Counter', 'Shred', 'Flee', 'Knockup', 'Knockback', 'Disarm', 'Grounded', 'Drowsy',
              'Asleep', 'Obscured', 'ClickProofToEnemies', 'Unkillable']
CAST, SELF, SLOT, SPENT, ENDGIVE = 0.6, 0.9, 0.9, 0.5, 0.8
NAMES = os.path.join(ROOT, 'data', 'lua1620', 'names.txt')


def own_scripts(champ):
    """the champion's script names (the 16.20 manifest's data/characters/<champion>/...) in lower case"""
    out = set()
    pre = f'data/characters/{champ.lower()}/'
    for l in open(NAMES):
        p = l.split('	')[1]
        if p.startswith(pre):
            out.add(p.rsplit('/', 1)[-1])
    return out


def lua(v, ind=''):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(round(v, 4))
    if isinstance(v, Raw):
        return str(v)
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, dict):
        return '{' + ', '.join(f'{k} = {lua(x, ind)}' for k, x in v.items()) + '}'
    if isinstance(v, list):
        if not v:
            return '{}'
        inner = ind + '  '
        return '{\n' + ',\n'.join(inner + lua(x, inner) for x in v) + '\n' + ind + '}'
    raise TypeError(v)


class Raw(str):
    """a Lua expression written as it is (a block function, an engine constant)"""


def block(fn, sub=None, **params):
    b = {'Function': Raw(fn), 'Params': params}
    if sub is not None:
        b['SubBlocks'] = sub
    return b


def write(champ):
    inf = json.load(open(os.path.join(INFER, f'{champ}.json')))
    from core import gamedata as G
    spells = [s for s in G.champion(champ).spells]
    low = {s.lower(): s for s in spells}
    scripts = {}                     # script name -> {event: [blocks]}
    notes = {}

    def ev(script, event):
        return scripts.setdefault(script, {}).setdefault(event, [])

    proper = {}                      # lower-case buff name -> a name with case (the spell's when it is one)
    for name in inf:
        proper[name] = low.get(name, name if not name.startswith('#') else name)
    mine = own_scripts(champ)
    for name, r in sorted(inf.items(), key=lambda x: -x[1]['n']):
        if r['n'] < 3:
            continue
        own = name in mine           # a buff of items, runes, the map has its script elsewhere: only given from here
        bname = proper[name]
        btype = BUFF_TYPES[r['type']] if r['type'] < len(BUFF_TYPES) else 'Internal'
        dur = r['durations'][0][0] if r['durations'] else 1.0
        add = {'BuffName': bname, 'BuffType': Raw('BUFF_' + btype), 'BuffAddType': Raw('BUFF_RENEW_EXISTING'),
               'Duration': dur, 'NumberOfStacks': 1, 'MaxStack': 1}
        if r['ticks'] and r['period_med'] and r['ticks'] / r['n'] >= 2:
            add['TickRate'] = r['period_med']        # its update actions at the rate its ticks came [a]
        used = []
        for (kind, *what), share in r['given_by']:
            if kind == 'cast' and share >= CAST and what and what[0] in low:
                if not own and r['self'] >= SELF:
                    continue         # not the champion's: an item's / rune's buff that comes with casts
                spell = low[what[0]]
                if r['self'] >= SELF:
                    ev(spell, 'SelfExecuteBuildingBlocks').append(block('BBSpellBuffAdd', TargetVar='Owner', AttackerVar='Owner', **add))
                elif r['self'] <= 1 - SELF:
                    ev(spell, 'TargetExecuteBuildingBlocks').append(block('BBSpellBuffAdd', TargetVar='Target', AttackerVar='Owner', **add))
                used.append(f'given by the cast of {spell} ({share:.2f})')
            elif kind == 'end' and share >= ENDGIVE and what and what[0] in mine and r['self'] <= 1 - SELF:
                giver = proper.get(what[0], what[0])
                ev(giver, '_on_spent').append(block('BBSpellBuffAdd', TargetVar='Target', AttackerVar='Owner', **add))
                used.append(f'given when {giver} is spent ({share:.2f})')
        if not own:
            notes.setdefault(bname, (r, used))
            continue
        # the slot it holds while it lasts: the spell's own buff's (the buffs a cast gives all begin in that frame)
        ends = {tuple(k): s for k, s in r['at_end']}
        main_buff = name in low or not any(k[0] == 'cast' and s2 >= CAST and k[1] in low and k[1] in inf for k, s2 in
                                          [(tuple(x), y) for x, y in r['given_by']])
        for (kind, *what), share in (r['at_add'] if main_buff else []):
            if kind == 'slot' and share >= SLOT:
                slot, spell = what
                ev(bname, 'OnBuffActivateBuildingBlocks').append(
                    block('BBSetSpell', SlotNumber=slot, SlotType=Raw('SpellSlots' if slot < 4 else 'ExtraSlots'),
                          SpellName=spell, TargetVar='Owner'))
                back = [k for k, s in ends.items() if k[0] == 'slot' and k[1] == slot and s >= SLOT]
                if back:
                    ev(bname, 'OnBuffDeactivateBuildingBlocks').append(
                        block('BBSetSpell', SlotNumber=slot, SlotType=Raw('SpellSlots' if slot < 4 else 'ExtraSlots'),
                              SpellName=back[0][2], TargetVar='Owner'))
                elif slot >= 4:
                    ev(bname, 'OnBuffDeactivateBuildingBlocks').append(
                        block('BBRemoveOverrideAutoAttack', OwnerVar='Owner'))
                used.append(f'slot {slot} = {spell} while it lasts ({share:.2f})')
        # effects: made in its first frame (share >= 0.9); taken away with it when they ended in its last frame
        fx_add = {w[0]: sh for (k, *w), sh in r['at_add'] if k == 'fx' and w and w[0]}
        fx_end = {w[0]: sh for (k, *w), sh in r['at_add'] if k == 'fx_until_end' and w}
        for key, sh in fx_add.items():
            if sh < SLOT:
                continue
            var = f'Fx{key:08x}'
            ev(bname, 'OnBuffActivateBuildingBlocks').append(
                block('BBSpellEffectCreate', EffectKey=key, BindObjectVar='Owner', EffectIDVar=var, EffectIDVarTable='InstanceVars'))
            used.append(f'effect {key:08x} at its start ({sh:.2f})')
            if fx_end.get(key, 0.0) >= 0.5 * sh:
                ev(bname, 'OnBuffDeactivateBuildingBlocks').append(
                    block('BBSpellEffectRemove', EffectIDVar=var, EffectIDVarTable='InstanceVars'))
                used.append(f'effect {key:08x} gone with it ({fx_end[key] / max(sh, 1e-9):.2f})')
        # spent by the holder's hit
        spent = sum(s for (k, *w), s in r['ends'] if k == 'my hit')
        if r['self'] >= SELF and spent >= SPENT:
            ev(bname, 'BuffOnHitUnitBuildingBlocks').append(block('Riot_Spent', name=bname))
            used.append(f'spent by the holder\'s hit ({spent:.2f})')
            # the hit that spends it carries the champion's own damage name (an attack the spell changed)
            for (kind, *what), share in r['ends']:
                if kind == 'my hit' and what and what[0] in mine and share >= 0.2:
                    ev(bname, 'OnBuffActivateBuildingBlocks').append(
                        block('BBOverrideAutoAttack', SpellName=what[0], OwnerVar='Owner'))
                    used.append(f'its hit is {what[0]} ({share:.2f})')
        # ticks
        if r['ticks'] and r['period_med'] and r['ticks'] / r['n'] >= 2:
            ev(bname, 'BuffOnUpdateActionsBuildingBlocks').append(
                block('BBExecutePeriodically', [
                    block('BBForEachUnitInTargetArea', [
                        block('BBApplyDamage', AttackerVar='Owner', TargetVar='Unit', SpellName=bname, DamageFromData=True)],
                        AttackerVar='Owner', CenterVar='Owner', RangeFromData=bname, Flags='AffectEnemies AffectNeutral AffectMinions AffectHeroes',
                        IteratorVar='Unit')],
                    TimeBetweenExecutions=r['period_med'], TrackTimeVar='LastTick', TrackTimeVarTable='InstanceVars',
                    ExecuteImmediately=False))
            used.append(f'damage ticks every {r["period_med"]} s ({r["ticks"]} ticks)')
        notes[bname] = (r, used)
    # a buff spent by a hit gives what its end gives, then goes
    for script, events in scripts.items():
        give = events.pop('_on_spent', [])
        for evname, blocks in events.items():
            for i, b in enumerate(blocks):
                if str(b['Function']) == 'Riot_Spent':
                    blocks[i:i + 1] = give + [block('BBSpellBuffRemoveCurrent', TargetVar='Owner')]
    # files
    d = os.path.join(OUT, champ)
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    for script, events in scripts.items():
        if script.lower() not in mine and script not in low.values():
            continue
        r, used = notes.get(script, ({'n': 0, 'games': 0}, []))
        head = [f'-- {script}: written by tools/bb_write16.py from the replays ({r.get("n", 0)} instances, {r.get("games", 0)} games)']
        head += [f'--   {u}' for u in used]
        body = [f'BuffName = {json.dumps(script)}'] + [f'{e} = {lua(b)}' for e, b in events.items() if b]
        open(os.path.join(d, script + '.lua'), 'w').write('\n'.join(head + body) + '\n')
    return scripts


def main():
    for champ in sys.argv[1:]:
        s = write(champ)
        print(champ, len(s), 'scripts ->', os.path.join(OUT, champ))


if __name__ == '__main__':
    main()
