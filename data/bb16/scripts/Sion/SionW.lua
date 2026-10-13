-- SionW: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "SionW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sionwshieldstacks", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sionwsoundshield", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}}
}
