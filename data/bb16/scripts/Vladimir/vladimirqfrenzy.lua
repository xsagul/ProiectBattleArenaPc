-- vladimirqfrenzy: written by tools/bb_write16.py from the replays (266 instances, 4 games)
--   spent by the holder's hit (0.72)
--   its hit is vladimirq (0.71)
BuffName = "vladimirqfrenzy"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "vladimirq", OwnerVar = "Owner"}}
}
