-- KledR: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "KledR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "kledrchargeshield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "kledrshieldcounter", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
