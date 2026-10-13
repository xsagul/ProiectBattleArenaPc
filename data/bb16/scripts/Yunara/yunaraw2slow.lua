-- yunaraw2slow: written by tools/bb_write16.py from the replays (132 instances, 15 games)
--   given when yunaraw2 is spent (1.00)
--   effect 02fa3b93 at its start (1.00)
BuffName = "yunaraw2slow"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 49953683, BindObjectVar = "Owner", EffectIDVar = "Fx02fa3b93", EffectIDVarTable = "InstanceVars"}}
}
