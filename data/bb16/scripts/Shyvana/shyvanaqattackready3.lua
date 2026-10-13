-- shyvanaqattackready3: written by tools/bb_write16.py from the replays (58 instances, 5 games)
--   spent by the holder's hit (0.91)
--   its hit is shyvanaqpassive (0.78)
BuffName = "shyvanaqattackready3"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "shyvanaqpassive", OwnerVar = "Owner"}}
}
