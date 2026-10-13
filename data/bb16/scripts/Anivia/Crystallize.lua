-- Crystallize: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "Crystallize"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "globalwallmarker", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "globalwallpush", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}}
}
