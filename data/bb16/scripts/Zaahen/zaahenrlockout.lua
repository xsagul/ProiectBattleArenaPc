-- zaahenrlockout: written by tools/bb_write16.py from the replays (49 instances, 6 games)
--   given by the cast of ZaahenR (1.00)
--   spent by the holder's hit (0.78)
--   its hit is zaahenr (0.73)
BuffName = "zaahenrlockout"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zaahenr", OwnerVar = "Owner"}}
}
