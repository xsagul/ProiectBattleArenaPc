-- CarpetBomb: BuildingBlocks Lua 5.1
BuffName = "CarpetBomb"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = MAGIC_DAMAGE, DamageFromData = true, BaseDamage = {150, 225, 300, 375, 450}, APRatio = 1.5, BonusADRatio = 2.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "dangerzone", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "valkyriesound", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.638, NumberOfStacks = 1, MaxStack = 1}}
}
