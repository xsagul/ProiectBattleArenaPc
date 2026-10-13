-- zaahenqbuff: written by tools/bb_write16.py from the replays (461 instances, 6 games)
--   given by the cast of ZaahenQ (1.00)
--   spent by the holder's hit (0.69)
--   its hit is zaahenq2attack (0.22)
BuffName = "zaahenqbuff"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "zaahenqknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zaahenq2attack", OwnerVar = "Owner"}}
}
