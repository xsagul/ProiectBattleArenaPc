-- threshepassive1: written by tools/bb_write16.py from the replays (1177 instances, 12 games)
--   spent by the holder's hit (0.52)
--   its hit is threshepassive (0.50)
BuffName = "threshepassive1"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "threshepassive", OwnerVar = "Owner"}}
}
