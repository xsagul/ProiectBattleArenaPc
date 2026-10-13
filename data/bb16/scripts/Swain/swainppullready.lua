-- swainppullready: written by tools/bb_write16.py from the replays (85 instances, 5 games)
--   slot 2 = SwainE2 while it lasts (1.00)
BuffName = "swainppullready"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SwainE2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SwainE", TargetVar = "Owner"}}
}
