-- khazixpdamage: written by tools/bb_write16.py from the replays (435 instances, 19 games)
--   effect 087658e1 at its start (1.66)
--   effect 087658e1 gone with it (0.90)
--   spent by the holder's hit (0.82)
--   its hit is khazixpassive (0.67)
BuffName = "khazixpdamage"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 141973729, BindObjectVar = "Owner", EffectIDVar = "Fx087658e1", EffectIDVarTable = "InstanceVars"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "khazixpassive", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx087658e1", EffectIDVarTable = "InstanceVars"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "khazixpslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
