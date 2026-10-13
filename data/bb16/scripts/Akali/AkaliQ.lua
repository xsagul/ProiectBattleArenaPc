-- AkaliQ: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "AkaliQ"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "akaliqslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "6653burn", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.9, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "2508burn", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.9, NumberOfStacks = 1, MaxStack = 1}}
}
