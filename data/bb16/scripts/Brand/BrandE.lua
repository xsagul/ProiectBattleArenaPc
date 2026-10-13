-- BrandE: Conflagration
BuffName = "BrandE"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BrandE", DamageFromData = true}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "brandablaze", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 3}}
}
