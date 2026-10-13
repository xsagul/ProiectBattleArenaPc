-- yuumipvisualtracker: written by tools/bb_write16.py from the replays (6 instances, 6 games)
--   slot 1 = YuumiWEndWrapper while it lasts (1.00)
BuffName = "yuumipvisualtracker"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "YuumiWEndWrapper", TargetVar = "Owner"}}
}
