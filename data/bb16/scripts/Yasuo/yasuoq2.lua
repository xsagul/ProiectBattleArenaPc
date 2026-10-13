-- yasuoq2: written by tools/bb_write16.py from the replays (1611 instances, 20 games)
--   slot 0 = YasuoQ3Wrapper while it lasts (1.00)
BuffName = "yasuoq2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "YasuoQ3Wrapper", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "YasuoQ1Wrapper", TargetVar = "Owner"}}
}
