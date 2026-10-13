-- kalistaexpungemarker: written by tools/bb_write16.py from the replays (4465 instances, 10 games)
--   effect 07ef7913 at its start (1.88)
--   effect 0ac0f283 at its start (1.88)
BuffName = "kalistaexpungemarker"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 133134611, BindObjectVar = "Owner", EffectIDVar = "Fx07ef7913", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
