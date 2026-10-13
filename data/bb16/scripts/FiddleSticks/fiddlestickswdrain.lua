-- fiddlestickswdrain: written by tools/bb_write16.py from the replays (876 instances, 3 games)
--   given by the cast of FiddleSticksW (0.99)
--   effect 04afea23 at its start (8.91)
--   effect 04afea23 gone with it (0.58)
BuffName = "fiddlestickswdrain"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
