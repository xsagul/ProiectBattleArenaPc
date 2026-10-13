-- dianaarcready: written by tools/bb_write16.py from the replays (2101 instances, 10 games)
--   spent by the holder's hit (0.91)
--   its hit is dianapassive (0.86)
BuffName = "dianaarcready"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "dianapassive", OwnerVar = "Owner"}}
}
