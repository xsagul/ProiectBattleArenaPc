-- AhriW: written by tools/bb_write16.py from the replays (2614 instances, 23 games)
--   given by the cast of AhriW (1.00)
--   slot 47 = AhriWMissile while it lasts (1.00)
--   effect 02ae29d1 at its start (1.00)
BuffName = "AhriW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ahriwspeedbuff", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AhriW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "AhriWMissile", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 44968401, BindObjectVar = "Owner", EffectIDVar = "Fx02ae29d1", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
