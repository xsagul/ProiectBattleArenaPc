-- BraumRWrapper: Glacial Fissure
BuffName = "BraumRWrapper"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BraumRWrapper", DamageFromData = true}},
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 1.0}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.4, Duration = 2.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "braumpulselineknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "braumpulselineslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
