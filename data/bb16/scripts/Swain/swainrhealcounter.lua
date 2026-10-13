-- swainrhealcounter: written by tools/bb_write16.py from the replays (35 instances, 5 games)
--   slot 3 = SwainRSoulFlare while it lasts (1.00)
BuffName = "swainrhealcounter"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "SwainRSoulFlare", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "SwainR", TargetVar = "Owner"}}
}
