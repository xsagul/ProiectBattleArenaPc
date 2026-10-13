-- kalistawsight: written by tools/bb_write16.py from the replays (34 instances, 10 games)
--   effect 00079664 at its start (1.00)
--   effect 00079664 gone with it (1.00)
BuffName = "kalistawsight"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}}
}
