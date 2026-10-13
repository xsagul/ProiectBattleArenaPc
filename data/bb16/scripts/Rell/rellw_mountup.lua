-- rellw_mountup: written by tools/bb_write16.py from the replays (178 instances, 8 games)
--   slot 1 = RellW_Dismount while it lasts (1.00)
BuffName = "rellw_mountup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RellW_Dismount", TargetVar = "Owner"}}
}
