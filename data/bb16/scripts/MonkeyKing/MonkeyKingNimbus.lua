-- MonkeyKingNimbus: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "MonkeyKingNimbus"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "monkeykingnimbuskick", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "monkeykingnimbuskickclone", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
