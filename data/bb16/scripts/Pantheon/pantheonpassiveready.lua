-- pantheonpassiveready: written by tools/bb_write16.py from the replays (461 instances, 7 games)
--   effect 0ac0f283 at its start (0.91)
--   effect 0ac0f283 gone with it (1.00)
BuffName = "pantheonpassiveready"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
