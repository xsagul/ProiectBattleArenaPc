-- camilleqprimingstart: written by tools/bb_write16.py from the replays (488 instances, 4 games)
--   slot 0 = CamilleQ2 while it lasts (1.00)
BuffName = "camilleqprimingstart"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "CamilleQ2", TargetVar = "Owner"}}
}
