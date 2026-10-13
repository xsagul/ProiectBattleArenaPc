-- Meditate: written by tools/bb_write16.py from the replays (312 instances, 6 games)
--   given by the cast of Meditate (1.00)
BuffName = "Meditate"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "Meditate", BuffType = BUFF_Heal, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
