-- CaitlynE: BuildingBlocks Lua 5.1
BuffName = "CaitlynE"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = MAGIC_DAMAGE, DamageFromData = true, BaseDamage = {80, 130, 180, 230, 280}, APRatio = 0.8}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.5, Duration = 1.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "caitlynemissile", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "caitlynpassivedriver", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
