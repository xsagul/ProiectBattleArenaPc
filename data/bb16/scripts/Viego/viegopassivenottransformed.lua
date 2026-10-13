-- viegopassivenottransformed: written by tools/bb_write16.py from the replays (92 instances, 6 games)
--   given by the cast of ViegoR (0.79)
--   spent by the holder's hit (1.00)
--   its hit is viegopassiveattack (0.81)
BuffName = "viegopassivenottransformed"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "viegopassiveattack", OwnerVar = "Owner"}}
}
