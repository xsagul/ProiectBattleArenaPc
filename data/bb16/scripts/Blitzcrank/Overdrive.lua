-- Overdrive: Overdrive
BuffName = "Overdrive"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "overdrive", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBIncStat, Params = {Stat = IncPercentMovementSpeedMod, Delta = 0.7, TargetVar = "Owner"}},
  {Function = BBIncStat, Params = {Stat = IncPercentAttackSpeedMod, Delta = 0.3, TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBIncStat, Params = {Stat = IncPercentMovementSpeedMod, Delta = -0.7, TargetVar = "Owner"}},
  {Function = BBIncStat, Params = {Stat = IncPercentAttackSpeedMod, Delta = -0.3, TargetVar = "Owner"}}
}
