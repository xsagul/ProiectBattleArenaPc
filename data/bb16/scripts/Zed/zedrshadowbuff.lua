-- zedrshadowbuff: written by tools/bb_write16.py from the replays (239 instances, 20 games)
--   effect 00079664 at its start (0.97)
BuffName = "zedrshadowbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}}
}
