-- LeeSinQOne: written by tools/bb_write16.py from the replays (906 instances, 9 games)
--   slot 0 = LeeSinQTwo while it lasts (0.96)
BuffName = "LeeSinQOne"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "LeeSinQTwo", TargetVar = "Owner"}}
}
