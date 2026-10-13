-- garenqhaste: written by tools/bb_write16.py from the replays (238 instances, 3 games)
--   given by the cast of GarenQ (0.99)
--   effect 00079664 at its start (1.00)
--   effect 07db875e at its start (1.00)
--   effect 0dc76864 at its start (1.00)
--   effect 0dc76866 at its start (1.00)
BuffName = "garenqhaste"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 131827550, BindObjectVar = "Owner", EffectIDVar = "Fx07db875e", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172196, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76864", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172198, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76866", EffectIDVarTable = "InstanceVars"}}
}
