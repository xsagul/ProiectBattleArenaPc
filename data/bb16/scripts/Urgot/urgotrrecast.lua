-- urgotrrecast: written by tools/bb_write16.py from the replays (32 instances, 3 games)
--   slot 3 = UrgotRRecast while it lasts (1.00)
BuffName = "urgotrrecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "UrgotRRecast", TargetVar = "Owner"}}
}
