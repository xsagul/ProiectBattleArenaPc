-- LeeSinR: written by tools/bb_write16.py from the replays (85 instances, 9 games)
--   given by the cast of LeeSinR (0.92)
BuffName = "LeeSinR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "leesinrroot", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.3, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "LeeSinR", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
