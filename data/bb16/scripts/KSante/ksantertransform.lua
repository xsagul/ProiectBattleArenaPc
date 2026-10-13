-- ksantertransform: written by tools/bb_write16.py from the replays (38 instances, 4 games)
--   slot 1 = KSanteW_AllOut while it lasts (1.00)
BuffName = "ksantertransform"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "KSanteW_AllOut", TargetVar = "Owner"}}
}
