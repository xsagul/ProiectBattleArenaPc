-- zacqmissile: written by tools/bb_write16.py from the replays (230 instances, 3 games)
--   effect 04afea23 at its start (0.95)
--   effect 04afea23 gone with it (0.98)
BuffName = "zacqmissile"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
