-- zedrtargetmark: written by tools/bb_write16.py from the replays (246 instances, 20 games)
--   given by the cast of ZedR (0.98)
--   slot 3 = ZedR2 while it lasts (0.98)
BuffName = "zedrtargetmark"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ZedR2", TargetVar = "Owner"}}
}
