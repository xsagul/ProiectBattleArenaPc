-- TrundleCircle: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "TrundleCircle"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "trundlewallbounce", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "globalwallmarker", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 100.0, NumberOfStacks = 1, MaxStack = 1}}
}
