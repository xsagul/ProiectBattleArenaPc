-- monkeykingnimbuskick: written by tools/bb_write16.py from the replays (1392 instances, 14 games)
--   given by the cast of MonkeyKingNimbus (1.00)
--   spent by the holder's hit (0.95)
--   its hit is monkeykingnimbus (0.89)
BuffName = "monkeykingnimbuskick"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "monkeykingnimbus", OwnerVar = "Owner"}}
}
