-- LuxLightStrikeKugel: written by tools/bb_write16.py from the replays (1176 instances, 10 games)
--   spent by the holder's hit (0.72)
--   its hit is luxlightstrikekugel (0.55)
BuffName = "LuxLightStrikeKugel"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "luxlightstrikekugel", OwnerVar = "Owner"}}
}
