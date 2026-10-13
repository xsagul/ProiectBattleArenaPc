-- YasuoR: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "YasuoR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "yasuorknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.1, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "yasuorarmorpen", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 15.0, NumberOfStacks = 1, MaxStack = 1}}
}
