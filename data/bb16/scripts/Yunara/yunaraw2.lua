-- yunaraw2: written by tools/bb_write16.py from the replays (118 instances, 15 games)
--   spent by the holder's hit (0.68)
--   its hit is yunaraw2 (0.67)
BuffName = "yunaraw2"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "yunaraw2slow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "yunaraw2", OwnerVar = "Owner"}}
}
