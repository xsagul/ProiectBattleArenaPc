-- GalioR: written by tools/bb_write16.py from the replays (42 instances, 5 games)
--   given by the cast of GalioR (1.00)
BuffName = "GalioR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "galiorshield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "GalioR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.25, NumberOfStacks = 1, MaxStack = 1}}
}
