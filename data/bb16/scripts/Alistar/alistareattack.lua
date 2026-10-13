-- alistareattack: written by tools/bb_write16.py from the replays (237 instances, 14 games)
--   spent by the holder's hit (0.79)
--   its hit is alistare (0.76)
BuffName = "alistareattack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "alistare", OwnerVar = "Owner"}}
}
