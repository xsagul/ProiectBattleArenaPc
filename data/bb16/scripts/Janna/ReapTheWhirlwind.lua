-- ReapTheWhirlwind: written by tools/bb_write16.py from the replays (121 instances, 16 games)
--   given by the cast of ReapTheWhirlwind (1.00)
BuffName = "ReapTheWhirlwind"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "jannamoveaway", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ReapTheWhirlwind", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
