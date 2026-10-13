-- MissileBarrage: BuildingBlocks Lua 5.1
BuffName = "MissileBarrage"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = PHYSICAL_DAMAGE, DamageFromData = true, BaseDamage = {90, 170, 250}, BonusADRatio = 0.85, APRatio = 0.2}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "corkimissilebarragenc", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "mbcheck2", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
