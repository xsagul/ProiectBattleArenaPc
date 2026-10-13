-- xerathqvfx: written by tools/bb_write16.py from the replays (824 instances, 7 games)
--   given by the cast of XerathArcanopulseChargeUp (0.98)
--   spent by the holder's hit (0.76)
--   its hit is xeratharcanopulse2 (0.61)
BuffName = "xerathqvfx"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "xeratharcanopulse2", OwnerVar = "Owner"}}
}
