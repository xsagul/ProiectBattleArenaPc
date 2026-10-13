-- zedwhandler: written by tools/bb_write16.py from the replays (1445 instances, 20 games)
--   given by the cast of ZedW (1.00)
--   slot 1 = ZedW2 while it lasts (1.00)
BuffName = "zedwhandler"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "ZedW2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "ZedW", TargetVar = "Owner"}}
}
