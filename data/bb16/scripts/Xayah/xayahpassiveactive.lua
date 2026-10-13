-- xayahpassiveactive: written by tools/bb_write16.py from the replays (710 instances, 8 games)
--   given by the cast of XayahQ (0.61)
--   slot 45 = XayahPassiveAttack while it lasts (1.00)
BuffName = "xayahpassiveactive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "XayahPassiveAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
