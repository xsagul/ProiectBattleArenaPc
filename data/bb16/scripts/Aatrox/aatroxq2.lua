-- aatroxq2: written by tools/bb_write16.py from the replays (649 instances, 8 games)
--   slot 0 = AatroxQ2 while it lasts (1.00)
--   slot 48 = AatroxQWrapperCast while it lasts (1.00)
--   spent by the holder's hit (0.73)
--   its hit is aatroxqwrappercast (0.69)
BuffName = "aatroxq2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "AatroxQ2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "AatroxQWrapperCast", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "aatroxqwrappercast", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
