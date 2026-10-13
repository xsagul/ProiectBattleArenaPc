-- IvernQ: written by tools/bb_write16.py from the replays (182 instances, 3 games)
--   slot 0 = IvernQRecast while it lasts (1.00)
BuffName = "IvernQ"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "IvernQRecast", TargetVar = "Owner"}}
}
