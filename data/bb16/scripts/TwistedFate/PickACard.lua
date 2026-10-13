-- PickACard: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "PickACard"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "pickacard_tracker", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
