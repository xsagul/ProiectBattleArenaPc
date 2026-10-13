-- viegopassivecasting: written by tools/bb_write16.py from the replays (87 instances, 6 games)
--   slot 49 = ViegoPassiveAttack while it lasts (1.00)
--   effect 04afea23 at its start (1.20)
--   effect 04afea23 gone with it (0.83)
BuffName = "viegopassivecasting"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "ViegoPassiveAttack", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
