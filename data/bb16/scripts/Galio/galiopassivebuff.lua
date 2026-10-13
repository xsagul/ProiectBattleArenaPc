-- galiopassivebuff: written by tools/bb_write16.py from the replays (612 instances, 5 games)
--   spent by the holder's hit (0.96)
--   its hit is galiopassiveattack (0.39)
BuffName = "galiopassivebuff"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "galiopassiveattack", OwnerVar = "Owner"}}
}
