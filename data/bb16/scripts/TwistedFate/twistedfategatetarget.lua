-- twistedfategatetarget: written by tools/bb_write16.py from the replays (42 instances, 7 games)
--   given when destiny_marker is spent (1.00)
--   given when destinyspellpassive is spent (1.00)
--   slot 3 = Destiny while it lasts (1.00)
BuffName = "twistedfategatetarget"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "Destiny", TargetVar = "Owner"}}
}
