-- hallucinateguide: written by tools/bb_write16.py from the replays (86 instances, 8 games)
--   slot 3 = HallucinateGuide while it lasts (1.00)
BuffName = "hallucinateguide"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "HallucinateGuide", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "HallucinateFull", TargetVar = "Owner"}}
}
