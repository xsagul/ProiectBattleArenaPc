-- caitlynpassivedriver: written by tools/bb_write16.py from the replays (639 instances, 9 games)
--   spent by the holder's hit (0.73)
--   its hit is caitlynpassive (0.69)
BuffName = "caitlynpassivedriver"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "caitlynpassive", OwnerVar = "Owner"}}
}
