-- FioraW: written by tools/bb_write16.py from the replays (153 instances, 7 games)
--   given by the cast of FioraW (1.00)
BuffName = "FioraW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "FioraW", BuffType = BUFF_SpellImmunity, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "fiorawblockccsound", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}}
}
