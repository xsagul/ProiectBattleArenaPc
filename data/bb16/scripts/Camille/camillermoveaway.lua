-- camillermoveaway: written by tools/bb_write16.py from the replays (35 instances, 4 games)
--   given when camilleruntargetable is spent (1.00)
--   effect 0d8164b3 at its start (3.00)
BuffName = "camillermoveaway"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 226583731, BindObjectVar = "Owner", EffectIDVar = "Fx0d8164b3", EffectIDVarTable = "InstanceVars"}}
}
