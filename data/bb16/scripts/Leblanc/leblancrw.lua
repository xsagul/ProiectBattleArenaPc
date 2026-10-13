-- leblancrw: written by tools/bb_write16.py from the replays (111 instances, 8 games)
--   slot 3 = LeblancRWReturn while it lasts (1.00)
BuffName = "leblancrw"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "LeblancRWReturn", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "LeblancRW", TargetVar = "Owner"}}
}
