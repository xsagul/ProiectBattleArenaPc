-- RyzeW: written by tools/bb_write16.py from the replays (81 instances, 3 games)
--   given by the cast of RyzeW (0.70)
BuffName = "RyzeW"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "RyzeW", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "ryzewroot", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
