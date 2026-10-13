-- pantheonpassive: written by tools/bb_write16.py from the replays (7 instances, 7 games)
--   effect 0f313b93 at its start (1.00)
--   effect 0ac0f283 at its start (1.00)
BuffName = "pantheonpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 254884755, BindObjectVar = "Owner", EffectIDVar = "Fx0f313b93", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
