-- taricwallybuff: written by tools/bb_write16.py from the replays (68 instances, 3 games)
--   given by the cast of TaricW (1.00)
--   effect 06b164d3 at its start (2.00)
--   effect 0076e4c2 at its start (1.00)
BuffName = "taricwallybuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 112288979, BindObjectVar = "Owner", EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 7791810, BindObjectVar = "Owner", EffectIDVar = "Fx0076e4c2", EffectIDVarTable = "InstanceVars"}}
}
