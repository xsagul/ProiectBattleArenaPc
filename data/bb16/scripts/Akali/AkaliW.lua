-- AkaliW: written by tools/bb_write16.py from the replays (161 instances, 7 games)
--   given by the cast of AkaliW (1.00)
BuffName = "AkaliW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AkaliW", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "akaliwhaste", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
