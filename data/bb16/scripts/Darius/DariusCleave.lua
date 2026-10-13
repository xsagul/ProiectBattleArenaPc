-- DariusCleave: BuildingBlocks Lua 5.1
BuffName = "DariusCleave"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "dariusqcast", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = PHYSICAL_DAMAGE, DamageFromData = true, BaseDamage = {50, 80, 110, 140, 170}, ADRatio = {1.0, 1.1, 1.2, 1.3, 1.4}}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "dariushemodot", BuffType = BUFF_Damage, BuffAddType = BUFF_STACKS_AND_RENEWS, Duration = 5.0, NumberOfStacks = 1, MaxStack = 5}}
}
