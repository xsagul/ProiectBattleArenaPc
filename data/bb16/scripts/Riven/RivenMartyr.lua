-- RivenMartyr: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "RivenMartyr"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "stun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.75, NumberOfStacks = 1, MaxStack = 1}}
}
