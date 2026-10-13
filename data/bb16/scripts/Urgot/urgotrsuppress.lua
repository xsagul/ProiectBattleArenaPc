-- urgotrsuppress: written by tools/bb_write16.py from the replays (18 instances, 3 games)
--   slot 50 = UrgotRFacing while it lasts (1.00)
--   effect 02fa3b93 at its start (1.00)
--   effect 02fa3b93 gone with it (1.00)
--   effect 0d113ba3 at its start (1.00)
--   effect 0d113ba3 gone with it (1.00)
BuffName = "urgotrsuppress"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "UrgotRFacing", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 49953683, BindObjectVar = "Owner", EffectIDVar = "Fx02fa3b93", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 219233187, BindObjectVar = "Owner", EffectIDVar = "Fx0d113ba3", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx02fa3b93", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0d113ba3", EffectIDVarTable = "InstanceVars"}}
}
