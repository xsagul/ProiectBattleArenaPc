-- AatroxR: written by tools/bb_write16.py from the replays (76 instances, 8 games)
--   given by the cast of AatroxR (0.93)
BuffName = "AatroxR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "flee", BuffType = BUFF_Flee, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "aatroxrfleeslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "aatroxrfx", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AatroxR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "aatroxrmovementspeedmanager", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}}
}
