-- khazixwevo: written by tools/bb_write16.py from the replays (10 instances, 19 games)
--   slot 49 = KhazixWEvo while it lasts (1.00)
--   slot 1 = KhazixWLong while it lasts (1.00)
BuffName = "khazixwevo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KhazixWEvo", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "KhazixWLong", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
