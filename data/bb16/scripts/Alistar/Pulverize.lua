-- Pulverize: written by tools/bb_write16.py from the replays (911 instances, 14 games)
--   given by the cast of Pulverize (0.88)
BuffName = "Pulverize"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "Pulverize", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
