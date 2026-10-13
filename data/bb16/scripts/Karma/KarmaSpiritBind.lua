-- KarmaSpiritBind: written by tools/bb_write16.py from the replays (369 instances, 13 games)
--   given by the cast of KarmaSpiritBind (0.98)
BuffName = "KarmaSpiritBind"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "globaltruesight", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "KarmaSpiritBind", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "karmawbeam", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "karmawbeammantra", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}}
}
