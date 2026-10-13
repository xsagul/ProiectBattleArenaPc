-- pykeqrange: written by tools/bb_write16.py from the replays (365 instances, 11 games)
--   effect 0ac0f283 at its start (0.95)
--   effect 0ac0f283 gone with it (1.00)
BuffName = "pykeqrange"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
