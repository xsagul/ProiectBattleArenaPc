-- UrgotR: written by tools/bb_write16.py from the replays (32 instances, 3 games)
--   given when urgotrspellpassive is spent (1.00)
--   slot 3 = UrgotRRecast while it lasts (1.00)
BuffName = "UrgotR"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "UrgotRRecast", TargetVar = "Owner"}}
}
