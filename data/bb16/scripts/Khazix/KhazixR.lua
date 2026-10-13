-- KhazixR: written by tools/bb_write16.py from the replays (245 instances, 19 games)
--   given by the cast of KhazixR (1.00)
BuffName = "KhazixR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "khazixrstealth", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "KhazixR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 12.0, NumberOfStacks = 1, MaxStack = 1}}
}
