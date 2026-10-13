-- zacqempowered: written by tools/bb_write16.py from the replays (225 instances, 3 games)
--   effect 04afea23 at its start (0.97)
--   effect 04afea23 gone with it (1.00)
--   spent by the holder's hit (0.85)
--   its hit is zacq (0.79)
BuffName = "zacqempowered"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zacq", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "zacqyankroot", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
