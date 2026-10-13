-- illaoiwattack: written by tools/bb_write16.py from the replays (312 instances, 4 games)
--   given by the cast of IllaoiW (0.76)
--   spent by the holder's hit (0.92)
--   its hit is illaoiw (0.33)
BuffName = "illaoiwattack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "illaoiw", OwnerVar = "Owner"}}
}
