-- ryzewroot: written by tools/bb_write16.py from the replays (60 instances, 3 games)
--   given by the cast of RyzeW (0.65)
--   effect 0102a113 at its start (0.97)
--   effect 0102a113 gone with it (0.98)
BuffName = "ryzewroot"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 16949523, BindObjectVar = "Owner", EffectIDVar = "Fx0102a113", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0102a113", EffectIDVarTable = "InstanceVars"}}
}
