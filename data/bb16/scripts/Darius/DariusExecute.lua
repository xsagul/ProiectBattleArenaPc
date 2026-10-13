-- DariusExecute: BuildingBlocks Lua 5.1
BuffName = "DariusExecute"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = TRUE_DAMAGE, DamageFromData = true, BaseDamage = {125, 250, 375}, BonusADRatio = 0.75}}
}
