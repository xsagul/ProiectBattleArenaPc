-- bardecreatedoor: written by tools/bb_write16.py from the replays (71 instances, 4 games)
--   given by the cast of BardE (0.99)
--   effect 00007b60 at its start (1.00)
--   effect 00007b60 gone with it (0.99)
BuffName = "bardecreatedoor"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 31584, BindObjectVar = "Owner", EffectIDVar = "Fx00007b60", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx00007b60", EffectIDVarTable = "InstanceVars"}}
}
