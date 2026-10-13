-- camilleedash1: written by tools/bb_write16.py from the replays (240 instances, 4 games)
--   slot 2 = CamilleEDash2 while it lasts (1.00)
BuffName = "camilleedash1"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "CamilleEDash2", TargetVar = "Owner"}}
}
