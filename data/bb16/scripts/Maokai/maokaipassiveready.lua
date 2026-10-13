-- maokaipassiveready: written by tools/bb_write16.py from the replays (95 instances, 3 games)
--   spent by the holder's hit (0.90)
--   its hit is maokaipassiveattack (0.73)
BuffName = "maokaipassiveready"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "maokaipassiveattack", OwnerVar = "Owner"}}
}
