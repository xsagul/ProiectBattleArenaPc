-- garenwshield: written by tools/bb_write16.py from the replays (83 instances, 3 games)
--   given by the cast of GarenW (1.00)
--   effect 06b164d3 at its start (1.00)
BuffName = "garenwshield"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 112288979, BindObjectVar = "Owner", EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}}
}
