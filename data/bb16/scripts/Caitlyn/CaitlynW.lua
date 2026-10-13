-- CaitlynW: written by tools/bb_write16.py from the replays (384 instances, 9 games)
--   given by the cast of CaitlynW (0.99)
BuffName = "CaitlynW"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "caitlynwsnare", BuffType = BUFF_Snare, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "caitlynwsight", BuffType = BUFF_Internal, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "caitlynpassivedriver", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = PHYSICAL_DAMAGE, DamageFromData = true, BaseDamage = {40, 85, 130, 175, 220}, BonusADRatio = 0.4}}
}

