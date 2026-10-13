-- ekkoeattackbuff: written by tools/bb_write16.py from the replays (1477 instances, 18 games)
--   given by the cast of EkkoE (0.98)
--   spent by the holder's hit (0.64)
BuffName = "ekkoeattackbuff"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "srt_2024_horde_dot_buff", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.6, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
