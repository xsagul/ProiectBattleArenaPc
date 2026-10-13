-- AzirQWrapper: Conquering Sands
BuffName = "AzirQWrapper"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "AzirQWrapper", DamageFromData = true}},
  {Function = BBApplySlow, Params = {AttackerVar = "Owner", TargetVar = "Target", SlowPercent = 0.25, Duration = 1.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "azirqdamage", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "azirqslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
