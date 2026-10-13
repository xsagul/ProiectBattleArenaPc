-- shenqtransmitter: written by tools/bb_write16.py from the replays (1816 instances, 12 games)
--   given by the cast of ShenQ (0.98)
--   effect 00007b60 at its start (1.00)
--   effect 00007b60 gone with it (1.00)
--   effect 0ac0f283 at its start (0.93)
BuffName = "shenqtransmitter"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 31584, BindObjectVar = "Owner", EffectIDVar = "Fx00007b60", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx00007b60", EffectIDVarTable = "InstanceVars"}}
}
