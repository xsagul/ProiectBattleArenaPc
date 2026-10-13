-- lissandrarself: written by tools/bb_write16.py from the replays (12 instances, 4 games)
--   given by the cast of LissandraR (0.83)
--   effect 08a58274 at its start (2.00)
--   effect 08a58274 gone with it (1.00)
BuffName = "lissandrarself"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 145064564, BindObjectVar = "Owner", EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
