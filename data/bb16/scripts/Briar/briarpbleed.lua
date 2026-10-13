-- briarpbleed: written by tools/bb_write16.py from the replays (437 instances, 3 games)
--   effect 04afea23 at its start (1.05)
--   effect 04afea23 gone with it (0.51)
BuffName = "briarpbleed"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
