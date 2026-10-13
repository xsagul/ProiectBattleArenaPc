-- olafwshield: written by tools/bb_write16.py from the replays (155 instances, 5 games)
--   given by the cast of OlafFrenziedStrikes (1.00)
--   effect 0dc76862 at its start (0.99)
--   effect 0dc76864 at its start (0.99)
BuffName = "olafwshield"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172194, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76862", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172196, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76864", EffectIDVarTable = "InstanceVars"}}
}
