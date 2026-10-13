-- zacemove: written by tools/bb_write16.py from the replays (387 instances, 3 games)
--   given by the cast of ZacE (1.00)
--   spent by the holder's hit (0.55)
--   its hit is zace (0.53)
BuffName = "zacemove"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "zacehitstun", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zace", OwnerVar = "Owner"}}
}
