-- SorakaE: written by tools/bb_write16.py from the replays (209 instances, 7 games)
--   given by the cast of SorakaE (0.92)
--   effect 0725e844 at its start (1.00)
BuffName = "SorakaE"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "silence", BuffType = BUFF_Silence, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.3, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sorakaepacify", BuffType = BUFF_Silence, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "SorakaE", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 119924804, BindObjectVar = "Owner", EffectIDVar = "Fx0725e844", EffectIDVarTable = "InstanceVars"}}
}
