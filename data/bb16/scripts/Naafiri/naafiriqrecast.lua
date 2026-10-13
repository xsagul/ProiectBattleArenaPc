-- naafiriqrecast: written by tools/bb_write16.py from the replays (501 instances, 5 games)
--   given by the cast of NaafiriQ (0.97)
--   slot 0 = NaafiriQRecast while it lasts (1.00)
BuffName = "naafiriqrecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "NaafiriQRecast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "NaafiriQ", TargetVar = "Owner"}}
}
