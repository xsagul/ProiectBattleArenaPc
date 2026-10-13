-- RyzeE: written by tools/bb_write16.py from the replays (1199 instances, 3 games)
--   effect 0ac0f283 at its start (2.45)
--   effect 0ac0f283 gone with it (0.84)
BuffName = "RyzeE"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
