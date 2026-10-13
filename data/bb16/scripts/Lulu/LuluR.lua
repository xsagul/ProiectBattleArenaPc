-- LuluR: written by tools/bb_write16.py from the replays (100 instances, 13 games)
--   given by the cast of LuluR (0.99)
BuffName = "LuluR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "lulurboom", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.25, NumberOfStacks = 1, MaxStack = 1}}
}
