-- gnartransform: written by tools/bb_write16.py from the replays (98 instances, 4 games)
--   slot 0 = GnarBigQ while it lasts (1.00)
--   slot 1 = GnarBigW while it lasts (1.00)
BuffName = "gnartransform"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "GnarBigQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "GnarBigW", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "GnarQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "GnarW", TargetVar = "Owner"}}
}
