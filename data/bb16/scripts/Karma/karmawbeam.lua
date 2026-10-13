-- karmawbeam: written by tools/bb_write16.py from the replays (332 instances, 13 games)
--   given by the cast of KarmaSpiritBind (0.99)
--   spent by the holder's hit (0.55)
--   its hit is karmaspiritbind (0.53)
BuffName = "karmawbeam"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "karmaspiritbindroot", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.6, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "karmaspiritbind", OwnerVar = "Owner"}}
}
