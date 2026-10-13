-- doublestrike: written by tools/bb_write16.py from the replays (1032 instances, 6 games)
--   slot 45 = MasterYiDoubleStrike while it lasts (1.00)
--   spent by the holder's hit (0.86)
--   its hit is masteryidoublestrike (0.27)
--   its hit is wujustyle (0.26)
BuffName = "doublestrike"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "MasterYiDoubleStrike", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "masteryidoublestrike", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "wujustyle", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
