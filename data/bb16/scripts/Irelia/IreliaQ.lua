-- IreliaQ: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "IreliaQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ireliapassivestacks", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ireliapassivestacksmax", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "item3153botrkstacks", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
