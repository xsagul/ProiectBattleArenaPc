-- BardQ: Cosmic Binding
BuffName = "BardQ"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BardQ", DamageFromData = true}},
  {Function = BBApplySlow, Params = {AttackerVar = "Owner", TargetVar = "Target", SlowPercent = 0.6, Duration = 1.4}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "bardqinitialtargetdebuff", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.4, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "bardqshackledebuff", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.4, NumberOfStacks = 1, MaxStack = 1}}
}
