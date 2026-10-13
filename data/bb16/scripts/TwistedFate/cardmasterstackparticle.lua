-- cardmasterstackparticle: written by tools/bb_write16.py from the replays (786 instances, 7 games)
--   spent by the holder's hit (0.92)
--   its hit is cardmasterstack (0.76)
BuffName = "cardmasterstackparticle"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "cardmasterstack", OwnerVar = "Owner"}}
}
