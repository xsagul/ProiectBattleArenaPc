-- leesinwmanager: written by tools/bb_write16.py from the replays (845 instances, 9 games)
--   given by the cast of LeeSinWOne (0.97)
--   slot 1 = LeeSinWTwo while it lasts (1.00)
BuffName = "leesinwmanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "LeeSinWTwo", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "LeeSinWOne", TargetVar = "Owner"}}
}
