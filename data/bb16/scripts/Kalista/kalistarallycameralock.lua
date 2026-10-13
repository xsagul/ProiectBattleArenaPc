-- kalistarallycameralock: written by tools/bb_write16.py from the replays (47 instances, 10 games)
--   given by the cast of KalistaRx (0.94)
--   effect 04afea23 at its start (1.00)
BuffName = "kalistarallycameralock"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
