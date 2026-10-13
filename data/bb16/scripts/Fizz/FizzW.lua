-- FizzW: written by tools/bb_write16.py from the replays (784 instances, 6 games)
--   given by the cast of FizzW (1.00)
--   spent by the holder's hit (0.94)
--   its hit is fizzw (0.51)
BuffName = "FizzW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "FizzW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "fizzw", OwnerVar = "Owner"}}
}
