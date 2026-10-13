-- leblancre: written by tools/bb_write16.py from the replays (10 instances, 8 games)
--   effect 04afea23 at its start (1.00)
--   effect 04afea23 gone with it (1.00)
BuffName = "leblancre"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
