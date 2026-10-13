-- BrandQ: Sear
BuffName = "BrandQ"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "BrandQ", DamageFromData = true}},
  {Function = BBIfHasBuff, Params = {TargetVar = "Target", BuffName = "brandablaze"}, SubBlocks = {
    {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 1.75}},
    {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "stun", BuffType = BUFF_Stun, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 1.75, NumberOfStacks = 1, MaxStack = 1}}
  }},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "brandablaze", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 3}}
}
