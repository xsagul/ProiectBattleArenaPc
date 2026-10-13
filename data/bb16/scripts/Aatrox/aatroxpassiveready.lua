-- aatroxpassiveready: written by tools/bb_write16.py from the replays (557 instances, 8 games)
--   spent by the holder's hit (0.94)
--   its hit is aatroxpassive (0.84)
BuffName = "aatroxpassiveready"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "aatroxpassive", OwnerVar = "Owner"}}
}
