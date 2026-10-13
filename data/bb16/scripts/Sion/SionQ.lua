-- SionQ: written by tools/bb_write16.py from the replays (279 instances, 4 games)
--   given by the cast of SionQ (1.00)
BuffName = "SionQ"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sionqsoundbeforehalfhit", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sionqslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.3, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "SionQ", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sionqsoundbeforehalf", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}}
}
