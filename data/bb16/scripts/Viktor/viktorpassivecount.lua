-- viktorpassivecount: written by tools/bb_write16.py from the replays (10 instances, 10 games)
--   spent by the holder's hit (0.88)
--   its hit is viktoremissile2 (0.38)
BuffName = "viktorpassivecount"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "viktoremissile2", OwnerVar = "Owner"}}
}
