-- kledwactive: written by tools/bb_write16.py from the replays (201 instances, 3 games)
--   slot 46 = KledWAttack1 while it lasts (1.00)
--   spent by the holder's hit (0.64)
BuffName = "kledwactive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "KledWAttack1", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
