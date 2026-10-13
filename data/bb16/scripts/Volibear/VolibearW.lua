-- VolibearW: written by tools/bb_write16.py from the replays (292 instances, 4 games)
--   given by the cast of VolibearW (0.99)
--   effect 0069eca4 at its start (1.00)
BuffName = "VolibearW"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "VolibearW", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 6941860, BindObjectVar = "Owner", EffectIDVar = "Fx0069eca4", EffectIDVarTable = "InstanceVars"}}
}
