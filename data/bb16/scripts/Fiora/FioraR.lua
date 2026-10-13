-- FioraR: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "FioraR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "fiorarmark", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "fiorarbuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
