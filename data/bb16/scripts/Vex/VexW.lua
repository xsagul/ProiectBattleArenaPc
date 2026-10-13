-- VexW: written by tools/bb_write16.py from the replays (173 instances, 5 games)
--   given by the cast of VexW (0.99)
BuffName = "VexW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "VexW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "elderdragonhealthbartickmanager", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
