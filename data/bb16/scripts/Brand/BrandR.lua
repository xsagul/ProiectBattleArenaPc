-- BrandR: Pyroclasm
BuffName = "BrandR"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BrandR", DamageFromData = true}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.45, Duration = 0.25}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "brandablaze", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 3}}
}
