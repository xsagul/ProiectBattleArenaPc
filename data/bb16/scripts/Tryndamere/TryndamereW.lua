-- TryndamereW: written by tools/bb_write16.py from the replays (281 instances, 10 games)
--   given by the cast of TryndamereW (1.00)
BuffName = "TryndamereW"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "TryndamereW", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "tryndamerewslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.25, NumberOfStacks = 1, MaxStack = 1}}
}
