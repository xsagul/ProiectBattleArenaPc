-- kledqmark: written by tools/bb_write16.py from the replays (77 instances, 3 games)
--   effect 00079664 at its start (1.00)
--   effect 00079664 gone with it (1.00)
--   effect 04afea23 at its start (1.00)
--   effect 04afea23 gone with it (1.00)
BuffName = "kledqmark"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
