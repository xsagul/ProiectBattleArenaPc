-- ViR: written by tools/bb_write16.py from the replays (20 instances, 3 games)
--   given by the cast of ViR (1.00)
--   effect 04afea23 at its start (1.00)
--   effect 04afea23 gone with it (1.00)
BuffName = "ViR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ViR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 7.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
