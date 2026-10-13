-- ziggsmoveawaycollision: written by tools/bb_write16.py from the replays (81 instances, 7 games)
--   slot 1 = ZiggsW while it lasts (1.00)
BuffName = "ziggsmoveawaycollision"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "ZiggsW", TargetVar = "Owner"}}
}
