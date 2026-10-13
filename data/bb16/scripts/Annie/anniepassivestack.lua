-- anniepassivestack: written by tools/bb_write16.py from the replays (161 instances, 3 games)
--   spent by the holder's hit (0.55)
--   its hit is annieq (0.33)
--   its hit is anniew (0.20)
BuffName = "anniepassivestack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "annieq", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "anniew", OwnerVar = "Owner"}}
}
