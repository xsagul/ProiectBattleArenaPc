-- yuumiqslow: written by tools/bb_write16.py from the replays (339 instances, 6 games)
--   given when yuumiqcast is spent (0.96)
--   slot 45 = YuumiQRelease while it lasts (1.00)
--   slot 0 = YuumiQ while it lasts (0.95)
BuffName = "yuumiqslow"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "YuumiQRelease", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "YuumiQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
