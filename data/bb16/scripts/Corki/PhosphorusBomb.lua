-- PhosphorusBomb: BuildingBlocks Lua 5.1
BuffName = "PhosphorusBomb"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = MAGIC_DAMAGE, DamageFromData = true, BaseDamage = {60, 105, 150, 195, 240}, ADRatio = 1.25, APRatio = 1.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "corkiphosphorusbombsight", BuffType = BUFF_Internal, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
