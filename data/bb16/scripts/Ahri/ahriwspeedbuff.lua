-- ahriwspeedbuff: written by tools/bb_write16.py from the replays (2614 instances, 23 games)
--   given by the cast of AhriW (1.00)
--   effect 02ae29d1 at its start (1.00)
BuffName = "ahriwspeedbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 44968401, BindObjectVar = "Owner", EffectIDVar = "Fx02ae29d1", EffectIDVarTable = "InstanceVars"}}
}
