-- ivernrminionspeed: written by tools/bb_write16.py from the replays (30 instances, 3 games)
--   given by the cast of IvernR (1.00)
--   slot 3 = IvernRRecast while it lasts (1.00)
BuffName = "ivernrminionspeed"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "IvernRRecast", TargetVar = "Owner"}}
}
