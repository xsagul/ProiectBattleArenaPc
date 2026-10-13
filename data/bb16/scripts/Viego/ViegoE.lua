-- ViegoE: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "ViegoE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "viegoehaste", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "viegoetimer", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
