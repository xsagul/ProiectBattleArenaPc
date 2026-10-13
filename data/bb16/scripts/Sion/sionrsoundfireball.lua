-- sionrsoundfireball: written by tools/bb_write16.py from the replays (41 instances, 4 games)
--   given by the cast of SionR (1.00)
--   spent by the holder's hit (0.61)
--   its hit is sionr (0.58)
BuffName = "sionrsoundfireball"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sionrtarget", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.809, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "sionr", OwnerVar = "Owner"}}
}
