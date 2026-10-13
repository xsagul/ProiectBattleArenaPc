-- ornnrrecastmanager: written by tools/bb_write16.py from the replays (45 instances, 5 games)
--   given by the cast of OrnnR (1.00)
--   slot 3 = OrnnRCharge while it lasts (1.00)
BuffName = "ornnrrecastmanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "OrnnRCharge", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "OrnnR", TargetVar = "Owner"}}
}
