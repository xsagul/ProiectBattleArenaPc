-- leesinwtwo: written by tools/bb_write16.py from the replays (707 instances, 9 games)
--   slot 1 = LeeSinWOne while it lasts (1.00)
BuffName = "leesinwtwo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "LeeSinWOne", TargetVar = "Owner"}}
}
