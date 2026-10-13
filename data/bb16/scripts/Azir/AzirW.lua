-- AzirW: Arise!
BuffName = "AzirW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "azirwsandsoldier", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 3}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "azirwspawnsound", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 3}}
}
