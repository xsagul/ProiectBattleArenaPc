-- karmawbeammantra: written by tools/bb_write16.py from the replays (35 instances, 13 games)
--   given by the cast of KarmaSpiritBind (0.97)
--   effect 06b164d3 at its start (1.00)
--   effect 06b164d3 gone with it (1.00)
--   effect 0ac0f283 at its start (1.00)
--   effect 0ac0f283 gone with it (1.00)
--   spent by the holder's hit (0.66)
--   its hit is karmamantra (0.63)
BuffName = "karmawbeammantra"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 112288979, BindObjectVar = "Owner", EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "karmamantra", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
