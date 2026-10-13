-- FeralScream: BuildingBlocks Lua 5.1
BuffName = "FeralScream"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = MAGIC_DAMAGE, DamageFromData = true, BaseDamage = {80, 130, 180, 230, 280}, APRatio = 0.7}},
  {Function = BBApplySilence, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = {1.6, 1.7, 1.8, 1.9, 2.0}}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "feralscream", BuffType = BUFF_Silence, BuffAddType = BUFF_RENEW_EXISTING, Duration = {1.6, 1.7, 1.8, 1.9, 2.0}, NumberOfStacks = 1, MaxStack = 1}}
}
