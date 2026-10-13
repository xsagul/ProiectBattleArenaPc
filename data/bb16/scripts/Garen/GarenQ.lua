-- GarenQ: written by tools/bb_write16.py from the replays (238 instances, 3 games)
--   given by the cast of GarenQ (0.99)
--   slot 45 = GarenQAttack while it lasts (1.00)
--   effect 00079664 at its start (1.00)
--   effect 00079664 gone with it (1.00)
--   effect 07db875e at its start (1.00)
--   effect 07db875e gone with it (1.00)
--   spent by the holder's hit (0.74)
--   its hit is garenqattack (0.32)
BuffName = "GarenQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "garenqhaste", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.6, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "GarenQ", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "GarenQAttack", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 131827550, BindObjectVar = "Owner", EffectIDVar = "Fx07db875e", EffectIDVarTable = "InstanceVars"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "garenqattack", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx07db875e", EffectIDVarTable = "InstanceVars"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "silence", BuffType = BUFF_Silence, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
