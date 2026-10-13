-- malphitethunderclap: written by tools/bb_write16.py from the replays (461 instances, 8 games)
--   given by the cast of Obduracy (1.00)
--   spent by the holder's hit (0.93)
--   its hit is malphitecleave (0.80)
BuffName = "malphitethunderclap"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "malphitecleave", OwnerVar = "Owner"}}
}
