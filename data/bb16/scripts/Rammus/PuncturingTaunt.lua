-- PuncturingTaunt: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "PuncturingTaunt"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "taunt", BuffType = BUFF_Taunt, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.2, NumberOfStacks = 1, MaxStack = 1}}
}
