-- yorickrbigghoul: written by tools/bb_write16.py from the replays (21 instances, 3 games)
--   slot 3 = YorickR2 while it lasts (1.00)
BuffName = "yorickrbigghoul"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "YorickR2", TargetVar = "Owner"}}
}
