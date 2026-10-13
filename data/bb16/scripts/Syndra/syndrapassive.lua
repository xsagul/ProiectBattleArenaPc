-- syndrapassive: written by tools/bb_write16.py from the replays (13 instances, 13 games)
--   effect 08a58274 at its start (3.00)
BuffName = "syndrapassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 145064564, BindObjectVar = "Owner", EffectIDVar = "Fx08a58274", EffectIDVarTable = "InstanceVars"}}
}
