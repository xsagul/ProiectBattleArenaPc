-- xayahfeathertracker: written by tools/bb_write16.py from the replays (48 instances, 8 games)
--   slot 49 = XayahRMissile while it lasts (1.00)
BuffName = "xayahfeathertracker"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "XayahRMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
