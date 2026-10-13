-- rivenwindslashready: written by tools/bb_write16.py from the replays (121 instances, 12 games)
--   given by the cast of RivenFengShuiEngine (0.65)
--   effect 02ae29d2 at its start (5.31)
BuffName = "rivenwindslashready"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 44968402, BindObjectVar = "Owner", EffectIDVar = "Fx02ae29d2", EffectIDVarTable = "InstanceVars"}}
}
