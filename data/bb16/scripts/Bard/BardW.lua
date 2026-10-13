-- BardW: Caretaker's Shrine
BuffName = "BardW"
SelfExecuteBuildingBlocks = {
  {Function = BBIncHealth, Params = {TargetVar = "Owner", Delta = 120.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "bardwspeedboost", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBIncHealth, Params = {TargetVar = "Target", Delta = 120.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "bardwspeedboost", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
