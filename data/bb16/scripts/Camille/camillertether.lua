-- camillertether: written by tools/bb_write16.py from the replays (39 instances, 4 games)
--   given when camilleruntargetable is spent (1.00)
--   effect 0d8164b3 at its start (3.00)
BuffName = "camillertether"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 226583731, BindObjectVar = "Owner", EffectIDVar = "Fx0d8164b3", EffectIDVarTable = "InstanceVars"}}
}
