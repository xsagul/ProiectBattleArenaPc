-- LeonaShieldOfDaybreak: written by tools/bb_write16.py from the replays (616 instances, 11 games)
--   given by the cast of LeonaShieldOfDaybreak (1.00)
--   spent by the holder's hit (0.84)
--   its hit is leonashieldofdaybreakattack (0.73)
BuffName = "LeonaShieldOfDaybreak"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "LeonaShieldOfDaybreak", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "3877maimdebuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "leonashieldofdaybreakattack", OwnerVar = "Owner"}}
}
