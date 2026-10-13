-- PowerFist: Power Fist
BuffName = "PowerFist"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "PowerFist", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "PowerFistAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "powerfistattack", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "PowerFistAttack", DamageFromData = true}},
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 1.0}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "powerfistslow", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
