-- VladimirE: written by tools/bb_write16.py from the replays (352 instances, 4 games)
--   given by the cast of VladimirE (1.00)
BuffName = "VladimirE"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "vladimireslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "2508burn", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.9, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "VladimirE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
