-- melrstackwatcher: written by tools/bb_write16.py from the replays (59 instances, 7 games)
--   spent by the holder's hit (0.88)
--   its hit is melr (0.68)
BuffName = "melrstackwatcher"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "melr", OwnerVar = "Owner"}}
}
