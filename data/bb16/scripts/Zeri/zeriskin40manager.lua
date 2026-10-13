-- zeriskin40manager: written by tools/bb_write16.py from the replays (7 instances, 9 games)
--   slot 47 = ZeriQBasicAttack while it lasts (1.00)
--   slot 47 = ZeriQBasicAttackEmpowered while it lasts (1.00)
BuffName = "zeriskin40manager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZeriQBasicAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZeriQBasicAttackEmpowered", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
