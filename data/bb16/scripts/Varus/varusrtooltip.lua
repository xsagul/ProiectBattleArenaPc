-- varusrtooltip: written by tools/bb_write16.py from the replays (25 instances, 4 games)
--   effect 007a7045 at its start (1.88)
BuffName = "varusrtooltip"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 8024133, BindObjectVar = "Owner", EffectIDVar = "Fx007a7045", EffectIDVarTable = "InstanceVars"}}
}
