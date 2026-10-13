-- AkshanR: written by tools/bb_write16.py from the replays (40 instances, 4 games)
--   given by the cast of AkshanR (1.00)
--   slot 3 = AkshanRCancel while it lasts (1.00)
--   slot 51 = AkshanRAmmo while it lasts (1.00)
--   effect 06b164d3 at its start (1.00)
--   effect 06b164d3 gone with it (1.00)
BuffName = "AkshanR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AkshanR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AkshanRCancel", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 51, SlotType = ExtraSlots, SpellName = "AkshanRAmmo", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 112288979, BindObjectVar = "Owner", EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AkshanR", TargetVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}}
}
