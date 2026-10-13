-- xerathrrampup: written by tools/bb_write16.py from the replays (52 instances, 7 games)
--   spent by the holder's hit (0.52)
--   its hit is xerathlocuspulse (0.48)
BuffName = "xerathrrampup"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "xerathlocuspulse", OwnerVar = "Owner"}}
}
