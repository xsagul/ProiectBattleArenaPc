-- syndrarvisual: written by tools/bb_write16.py from the replays (146 instances, 13 games)
--   effect 08a58274 at its start (3.43)
--   effect 08a58274 gone with it (0.74)
BuffName = "syndrarvisual"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 145064564, BindObjectVar = "Owner", EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
