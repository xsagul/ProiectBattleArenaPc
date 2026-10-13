-- doublestrikestacks: written by tools/bb_write16.py from the replays (1276 instances, 6 games)
--   spent by the holder's hit (0.62)
--   its hit is wujustyle (0.24)
BuffName = "doublestrikestacks"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "wujustyle", OwnerVar = "Owner"}}
}
