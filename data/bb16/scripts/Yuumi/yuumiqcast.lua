-- yuumiqcast: written by tools/bb_write16.py from the replays (547 instances, 6 games)
--   given by the cast of YuumiQ (0.98)
--   slot 45 = YuumiQCast while it lasts (1.00)
BuffName = "yuumiqcast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "YuumiQCast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "YuumiQRelease", TargetVar = "Owner"}}
}
