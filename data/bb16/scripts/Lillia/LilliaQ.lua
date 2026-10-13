-- LilliaQ: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "LilliaQ"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "lilliapdot", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "lilliaprancematerial", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 999.0, NumberOfStacks = 1, MaxStack = 1}}
}
