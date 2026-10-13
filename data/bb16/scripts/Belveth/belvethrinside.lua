-- belvethrinside: written by tools/bb_write16.py from the replays (72 instances, 4 games)
--   given by the cast of BelvethR (0.85)
--   effect 04afea23 at its start (4.01)
--   effect 04afea23 gone with it (0.97)
BuffName = "belvethrinside"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
