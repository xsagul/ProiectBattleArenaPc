-- jaycehypercharge: written by tools/bb_write16.py from the replays (411 instances, 8 games)
--   spent by the holder's hit (0.54)
--   its hit is jaycerangedattack (0.33)
BuffName = "jaycehypercharge"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaycerangedattack", OwnerVar = "Owner"}}
}
