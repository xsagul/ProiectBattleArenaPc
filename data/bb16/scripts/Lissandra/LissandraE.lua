-- LissandraE: written by tools/bb_write16.py from the replays (162 instances, 4 games)
--   slot 2 =  while it lasts (1.00)
BuffName = "LissandraE"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "\u0007", TargetVar = "Owner"}}
}
