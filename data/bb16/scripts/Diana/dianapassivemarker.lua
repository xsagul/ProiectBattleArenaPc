-- dianapassivemarker: written by tools/bb_write16.py from the replays (2399 instances, 10 games)
--   spent by the holder's hit (0.77)
--   its hit is dianapassive (0.73)
BuffName = "dianapassivemarker"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "dianapassive", OwnerVar = "Owner"}}
}
