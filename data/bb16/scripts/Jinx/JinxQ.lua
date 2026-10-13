-- JinxQ: written by tools/bb_write16.py from the replays (780 instances, 10 games)
--   given by the cast of JinxQ (1.00)
BuffName = "JinxQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "jinxqicon", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "JinxQ", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
