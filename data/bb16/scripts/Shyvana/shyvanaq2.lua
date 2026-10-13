-- shyvanaq2: written by tools/bb_write16.py from the replays (574 instances, 5 games)
--   given by the cast of ShyvanaQ (0.77)
--   slot 0 = ShyvanaQ2 while it lasts (1.00)
BuffName = "shyvanaq2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ShyvanaQ2", TargetVar = "Owner"}}
}
