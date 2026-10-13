-- DariusAxeGrabCone: BuildingBlocks Lua 5.1
BuffName = "DariusAxeGrabCone"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "DariusAxeGrabCone", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.4, Duration = 1.0}}
}
