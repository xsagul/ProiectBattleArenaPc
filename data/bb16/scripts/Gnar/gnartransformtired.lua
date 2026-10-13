-- gnartransformtired: written by tools/bb_write16.py from the replays (86 instances, 4 games)
--   slot 0 = GnarQ while it lasts (1.00)
--   slot 1 = GnarW while it lasts (1.00)
--   slot 2 = GnarE while it lasts (1.00)
BuffName = "gnartransformtired"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "GnarQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "GnarW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "GnarE", TargetVar = "Owner"}}
}
