-- vorpalspikesdebuff: written by tools/bb_write16.py from the replays (3778 instances, 15 games)
--   effect 06b164d3 at its start (1.22)
BuffName = "vorpalspikesdebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 112288979, BindObjectVar = "Owner", EffectIDVar = "Fx06b164d3", EffectIDVarTable = "InstanceVars"}}
}
