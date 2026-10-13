-- ahripassivecounter: written by tools/bb_write16.py from the replays (587 instances, 23 games)
--   spent by the holder's hit (0.98)
--   its hit is ahriq (0.55)
BuffName = "ahripassivecounter"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "ahriq", OwnerVar = "Owner"}}
}
