-- syndrapassiveeupgrade: written by tools/bb_write16.py from the replays (13 instances, 13 games)
--   slot 2 = SyndraE5 while it lasts (1.00)
BuffName = "syndrapassiveeupgrade"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SyndraE5", TargetVar = "Owner"}}
}
