-- JayceThunderingBlow: written by tools/bb_write16.py from the replays (111 instances, 8 games)
--   given by the cast of JayceThunderingBlow (0.99)
BuffName = "JayceThunderingBlow"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "jaycethunderingblowroot", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.3, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "jayceknockedbuff", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "JayceThunderingBlow", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}}
}
