-- VolibearQ: written by tools/bb_write16.py from the replays (212 instances, 4 games)
--   given by the cast of VolibearQ (1.00)
--   spent by the holder's hit (0.57)
BuffName = "VolibearQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "VolibearQ", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "stun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
