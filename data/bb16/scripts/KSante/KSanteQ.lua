-- KSanteQ: written by tools/bb_write16.py from the replays (470 instances, 4 games)
--   spent by the holder's hit (0.69)
--   its hit is ksanteq (0.61)
BuffName = "KSanteQ"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "ksanteq", OwnerVar = "Owner"}}
}
