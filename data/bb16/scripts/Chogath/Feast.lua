-- Feast: BuildingBlocks Lua 5.1
BuffName = "Feast"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "eyeshrinebuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 20.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = TRUE_DAMAGE, DamageFromData = true, BaseDamage = {300, 475, 650}, APRatio = 0.5, BonusHPRatio = 0.1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "Feast", BuffType = BUFF_Counter, BuffAddType = BUFF_STACKS_AND_RENEWS, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 255}}
}
