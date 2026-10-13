-- viktorrkilltracker: written by tools/bb_write16.py from the replays (38 instances, 10 games)
--   given by the cast of ViktorR (1.00)
--   slot 3 = ViktorRGuide while it lasts (1.00)
BuffName = "viktorrkilltracker"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ViktorRGuide", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ViktorR", TargetVar = "Owner"}}
}
