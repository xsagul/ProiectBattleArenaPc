-- OlafFrenziedStrikes: written by tools/bb_write16.py from the replays (155 instances, 5 games)
--   given by the cast of OlafFrenziedStrikes (1.00)
--   effect 0dc76862 at its start (0.99)
--   effect 0dc76862 gone with it (0.98)
--   effect 0dc76864 at its start (0.99)
--   effect 0dc76864 gone with it (0.98)
BuffName = "OlafFrenziedStrikes"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "OlafFrenziedStrikes", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "olafwshield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172194, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76862", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172196, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76864", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0dc76862", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0dc76864", EffectIDVarTable = "InstanceVars"}}
}
