-- IvernR: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "IvernR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ivernrrecast", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 45.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "ivernrminionspeed", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
