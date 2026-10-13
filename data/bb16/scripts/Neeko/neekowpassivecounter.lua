-- neekowpassivecounter: written by tools/bb_write16.py from the replays (250 instances, 3 games)
--   spent by the holder's hit (0.96)
--   its hit is neekobasicattack (0.54)
BuffName = "neekowpassivecounter"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "neekobasicattack", OwnerVar = "Owner"}}
}
