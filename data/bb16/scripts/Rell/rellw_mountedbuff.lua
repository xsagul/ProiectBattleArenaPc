-- rellw_mountedbuff: written by tools/bb_write16.py from the replays (231 instances, 8 games)
--   slot 1 = RellW_Dismount while it lasts (0.93)
BuffName = "rellw_mountedbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RellW_Dismount", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RellW_MountUp", TargetVar = "Owner"}}
}
