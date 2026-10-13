-- AhriR: written by tools/bb_write16.py from the replays (249 instances, 23 games)
--   given by the cast of AhriR (0.98)
--   effect 0102a113 at its start (2.00)
--   effect 02ae29d1 at its start (1.02)
BuffName = "AhriR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AhriR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 14.7, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 16949523, BindObjectVar = "Owner", EffectIDVar = "Fx0102a113", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 44968401, BindObjectVar = "Owner", EffectIDVar = "Fx02ae29d1", EffectIDVarTable = "InstanceVars"}}
}
