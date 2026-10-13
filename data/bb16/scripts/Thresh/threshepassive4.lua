-- threshepassive4: written by tools/bb_write16.py from the replays (436 instances, 12 games)
--   spent by the holder's hit (0.88)
--   its hit is threshepassive (0.79)
BuffName = "threshepassive4"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "threshepassive", OwnerVar = "Owner"}}
}
