-- threshwlanternout: written by tools/bb_write16.py from the replays (334 instances, 12 games)
--   effect 0d02dec4 at its start (1.00)
--   effect 0d02dec4 gone with it (0.99)
--   effect 0d02e654 at its start (1.00)
--   effect 0d02e654 gone with it (0.99)
BuffName = "threshwlanternout"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 218291908, BindObjectVar = "Owner", EffectIDVar = "Fx0d02dec4", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 218293844, BindObjectVar = "Owner", EffectIDVar = "Fx0d02e654", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0d02dec4", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0d02e654", EffectIDVarTable = "InstanceVars"}}
}
