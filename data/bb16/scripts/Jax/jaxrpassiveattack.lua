-- jaxrpassiveattack: written by tools/bb_write16.py from the replays (560 instances, 3 games)
--   spent by the holder's hit (0.81)
--   its hit is jaxrpassive (0.79)
BuffName = "jaxrpassiveattack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaxrpassive", OwnerVar = "Owner"}}
}
