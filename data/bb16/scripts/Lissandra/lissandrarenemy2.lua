-- lissandrarenemy2: written by tools/bb_write16.py from the replays (33 instances, 4 games)
--   given when lissandrarenemy is spent (1.00)
--   effect 08a58274 at its start (0.97)
--   effect 08a58274 gone with it (1.00)
BuffName = "lissandrarenemy2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 145064564, BindObjectVar = "Owner", EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
