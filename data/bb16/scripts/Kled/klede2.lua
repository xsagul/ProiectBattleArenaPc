-- klede2: written by tools/bb_write16.py from the replays (36 instances, 3 games)
--   slot 2 = KledE2 while it lasts (1.00)
BuffName = "klede2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KledE2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KledE", TargetVar = "Owner"}}
}
