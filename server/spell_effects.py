"""What a spell does on the client besides its cast (49) and animation (65): the buffs the server puts (693) and takes
off (522) and held animations (65 with a duration), per champion spell.

Where every piece comes from:
- buff names: the spell scripts' stubs in Scripts.wad (13.3), `BuffName` (data/lua133: GarenQ.lua -> "GarenQBuff",
  GarenQHaste.lua -> "GarenQHaste", GarenW.lua -> "GarenW", GarenE.lua -> "GarenE");
- durations: the spell's data values per rank (spell_info.py, mDataValues): GarenQ MovementSpeedDuration (haste),
  AttackWindow (the empowered attack), GarenW DRDuration, GarenE Duration -- chosen by their names [deduced];
- buff type (693 +0x34) and +0x16: NOT in the data. Taken by analogy with the replay (data/exe133/codec/
  693.all.jsonl): self buffs given at cast by Jax (JaxCounterStrike, JaxEmpowerTwo, JaxRApexForm) are type 2 with
  +0x16 = 3; haste buffs (JhinPassiveHaste, FleetFootworkHaste) are type 15 [analogy, to verify against the real game];
- held animation: 65 +0x24 = how long the clip is held (replay: crab_hide 5.0, Jax Spell3 2.25 s) [deduced]; Garen E
  has no mAnimationName, its clip "Spell3" is the parametric spin of the animation graph (fnv("spell3") = 0xb4f63b8e).
"""

EFFECTS = {
    'GarenQ': [('buff', 'GarenQHaste', 'MovementSpeedDuration', 15),
               ('buff', 'GarenQBuff', 'AttackWindow', 2)],
    'GarenW': [('buff', 'GarenW', 'DRDuration', 2)],
    'GarenE': [('buff', 'GarenE', 'Duration', 2),
               ('hold', 'Spell3', 'Duration', None)],
}


def effects(spell, data, rank):
    """[(kind, name, seconds, buff type)] for a cast of the spell at that rank; data = spell_info.spells()[spell]"""
    import spell_info as SI
    out = []
    for kind, name, value, btype in EFFECTS.get(spell, []):
        vals = data.get('values', {}).get(value)
        if vals:
            out.append((kind, name, SI.at_level(vals, rank), btype))
    return out
