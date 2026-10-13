-- ForcePulse: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "ForcePulse"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "slow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
