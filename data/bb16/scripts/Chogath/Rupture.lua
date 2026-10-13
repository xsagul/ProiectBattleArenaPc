-- Rupture: BuildingBlocks Lua 5.1
BuffName = "Rupture"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = MAGIC_DAMAGE, DamageFromData = true, BaseDamage = {80, 135, 190, 245, 300}, APRatio = 1.0}},
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 1.0}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.6, Duration = 1.5}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "rupturetarget", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "rupturetargetslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
