-- gragaswattackbuff: written by tools/bb_write16.py from the replays (1031 instances, 7 games)
--   spent by the holder's hit (0.76)
--   its hit is gragasw (0.42)
BuffName = "gragaswattackbuff"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "gragasw", OwnerVar = "Owner"}}
}
