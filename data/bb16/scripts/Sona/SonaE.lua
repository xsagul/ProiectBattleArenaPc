-- SonaE: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "SonaE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sonaeselfhaste", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 7.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sonaambientesound", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "sonaepassiveattack", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sonaehaste", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
