-- CaitlynR: written by tools/bb_write16.py from the replays (61 instances, 9 games)
--   given by the cast of CaitlynR (1.00)
BuffName = "CaitlynR"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "CaitlynR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBApplyDamage, Params = {TargetVar = "Target", AttackerVar = "Owner", DamageType = PHYSICAL_DAMAGE, DamageFromData = true, BaseDamage = {300, 500, 700}, BonusADRatio = 1.7}}
}

