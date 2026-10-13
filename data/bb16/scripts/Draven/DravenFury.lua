-- DravenFury: written by tools/bb_write16.py from the replays (1599 instances, 11 games)
--   given by the cast of DravenFury (0.99)
BuffName = "DravenFury"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "DravenFury", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "dravenfurybuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
