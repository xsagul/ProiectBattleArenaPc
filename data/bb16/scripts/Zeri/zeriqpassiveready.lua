-- zeriqpassiveready: written by tools/bb_write16.py from the replays (699 instances, 9 games)
--   slot 47 = ZeriQBasicAttackEmpowered while it lasts (1.00)
--   spent by the holder's hit (0.95)
--   its hit is zeriqbasicattackempowered (0.93)
BuffName = "zeriqpassiveready"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZeriQBasicAttackEmpowered", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zeriqbasicattackempowered", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZeriQBasicAttack", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
