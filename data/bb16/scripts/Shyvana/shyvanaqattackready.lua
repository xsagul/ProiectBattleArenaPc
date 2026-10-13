-- shyvanaqattackready: written by tools/bb_write16.py from the replays (585 instances, 5 games)
--   given by the cast of ShyvanaQ (0.99)
--   spent by the holder's hit (0.96)
--   its hit is shyvanaqpassive (0.87)
BuffName = "shyvanaqattackready"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "shyvanaqpassive", OwnerVar = "Owner"}}
}
