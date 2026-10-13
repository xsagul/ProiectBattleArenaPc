-- GragasE: written by tools/bb_write16.py from the replays (701 instances, 7 games)
--   given by the cast of GragasE (1.00)
--   spent by the holder's hit (0.72)
--   its hit is gragase (0.60)
BuffName = "GragasE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "GragasE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "eternals_gragasflashedtracker", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "stun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "gragasestun", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "gragase", OwnerVar = "Owner"}}
}
