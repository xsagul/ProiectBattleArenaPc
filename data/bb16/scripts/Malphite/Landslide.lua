-- Landslide: written by tools/bb_write16.py from the replays (0 instances, 0 games)
BuffName = "Landslide"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "landslidedebuff", BuffType = BUFF_AttackSpeedSlow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
