-- morganardebuff: written by tools/bb_write16.py from the replays (45 instances, 4 games)
--   effect 04afea23 at its start (1.62)
--   effect 04afea23 gone with it (0.79)
--   effect 0dea3ae3 at its start (1.60)
BuffName = "morganardebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 233454307, BindObjectVar = "Owner", EffectIDVar = "Fx0dea3ae3", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
