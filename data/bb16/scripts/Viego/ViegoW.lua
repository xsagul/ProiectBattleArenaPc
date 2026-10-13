-- ViegoW: written by tools/bb_write16.py from the replays (592 instances, 6 games)
--   given by the cast of ViegoW (1.00)
BuffName = "ViegoW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ViegoW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "viegowdash", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "viegowmis", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.317, NumberOfStacks = 1, MaxStack = 1}}
}
