-- KaisaR: written by tools/bb_write16.py from the replays (91 instances, 14 games)
--   given by the cast of KaisaR (1.00)
BuffName = "KaisaR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "KaisaR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "kaisarshield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "kaisarready", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "kaisaskin71goldglow", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 16.0, NumberOfStacks = 1, MaxStack = 1}}
}
