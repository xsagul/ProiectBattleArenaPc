-- BelvethW: Above and Below
BuffName = "BelvethW"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BelvethW", DamageFromData = true}},
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 0.75}},
  {Function = BBApplySlow, Params = {TargetVar = "Target", AttackerVar = "Owner", SlowPercent = 0.3, Duration = 2.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "belvethwknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 0.75, NumberOfStacks = 1, MaxStack = 1}}
}
