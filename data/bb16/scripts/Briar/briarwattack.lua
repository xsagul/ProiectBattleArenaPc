-- briarwattack: written by tools/bb_write16.py from the replays (228 instances, 3 games)
--   slot 46 = BriarWAttack while it lasts (0.98)
--   slot 1 = BriarW while it lasts (0.98)
--   spent by the holder's hit (0.79)
--   its hit is briarwattack (0.33)
--   its hit is briarw (0.23)
BuffName = "briarwattack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "BriarWAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "BriarW", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "briarwattack", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "briarw", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
