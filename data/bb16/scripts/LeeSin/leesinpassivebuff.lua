-- leesinpassivebuff: written by tools/bb_write16.py from the replays (1673 instances, 9 games)
--   spent by the holder's hit (0.53)
--   its hit is leesinbasicattack (0.51)
BuffName = "leesinpassivebuff"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "leesinbasicattack", OwnerVar = "Owner"}}
}
