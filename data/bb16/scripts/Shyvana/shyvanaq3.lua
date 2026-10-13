-- shyvanaq3: written by tools/bb_write16.py from the replays (62 instances, 5 games)
--   slot 0 = ShyvanaQ3 while it lasts (1.00)
BuffName = "shyvanaq3"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ShyvanaQ3", TargetVar = "Owner"}}
}
