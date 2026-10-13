-- pantheonefacinglock: written by tools/bb_write16.py from the replays (132 instances, 7 games)
--   given by the cast of PantheonE (1.00)
--   spent by the holder's hit (0.60)
--   its hit is pantheoneshieldslam (0.59)
BuffName = "pantheonefacinglock"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "pantheoneshieldslam", OwnerVar = "Owner"}}
}
