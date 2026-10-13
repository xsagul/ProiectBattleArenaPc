-- Feast: written by tools/bb_write16.py from the replays (15 instances, 15 games)
BuffName = "Feast"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "eyeshrinebuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 20.0, NumberOfStacks = 1, MaxStack = 1}}
}
