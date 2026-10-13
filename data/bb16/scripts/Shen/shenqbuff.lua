-- shenqbuff: written by tools/bb_write16.py from the replays (1809 instances, 12 games)
--   slot 46 = ShenQAttack while it lasts (1.00)
--   spent by the holder's hit (0.58)
--   its hit is shenq (0.56)
BuffName = "shenqbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ShenQAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "shenq", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
