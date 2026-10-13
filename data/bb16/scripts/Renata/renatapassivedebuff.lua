-- renatapassivedebuff: written by tools/bb_write16.py from the replays (642 instances, 6 games)
--   effect 04afea23 at its start (1.00)
BuffName = "renatapassivedebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
