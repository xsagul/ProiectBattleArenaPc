-- renataqselfroot: written by tools/bb_write16.py from the replays (177 instances, 6 games)
--   given by the cast of RenataQ (1.00)
--   spent by the holder's hit (0.71)
--   its hit is renataq (0.68)
BuffName = "renataqselfroot"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "RenataQ", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "renataq", OwnerVar = "Owner"}}
}
