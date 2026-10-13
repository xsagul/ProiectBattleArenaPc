-- yasuoq1: written by tools/bb_write16.py from the replays (2070 instances, 20 games)
--   slot 0 = YasuoQ2Wrapper while it lasts (1.00)
--   spent by the holder's hit (0.72)
--   its hit is yasuoq2 (0.35)
BuffName = "yasuoq1"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "YasuoQ2Wrapper", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "yasuoq2", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
