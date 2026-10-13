-- aurorapspiritmode: Spirit Mode
BuffName = "aurorapspiritmode"
OnBuffActivateBuildingBlocks = {
  {Function = BBIncStat, Params = {Stat = IncPercentMovementSpeedMod, Delta = 0.05, TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBIncStat, Params = {Stat = IncPercentMovementSpeedMod, Delta = -0.05, TargetVar = "Owner"}}
}
