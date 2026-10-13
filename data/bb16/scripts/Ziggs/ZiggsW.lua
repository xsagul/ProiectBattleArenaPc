-- ZiggsW: written by tools/bb_write16.py from the replays (246 instances, 7 games)
--   spent by the holder's hit (0.63)
--   its hit is ziggsw (0.56)
BuffName = "ZiggsW"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "moveawaycollision", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "ziggsw", OwnerVar = "Owner"}}
}
