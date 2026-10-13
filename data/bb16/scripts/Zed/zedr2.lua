-- zedr2: written by tools/bb_write16.py from the replays (242 instances, 20 games)
--   given by the cast of ZedR (1.00)
--   slot 3 = ZedR2 while it lasts (1.00)
BuffName = "zedr2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ZedR2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ZedR", TargetVar = "Owner"}}
}
