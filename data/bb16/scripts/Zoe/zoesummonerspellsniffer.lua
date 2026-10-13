-- zoesummonerspellsniffer: written by tools/bb_write16.py from the replays (40 instances, 8 games)
--   effect 0f313b93 at its start (2.27)
BuffName = "zoesummonerspellsniffer"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 254884755, BindObjectVar = "Owner", EffectIDVar = "Fx0f313b93", EffectIDVarTable = "InstanceVars"}}
}
