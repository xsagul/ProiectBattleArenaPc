-- KSanteW: written by tools/bb_write16.py from the replays (191 instances, 4 games)
--   given by the cast of KSanteW (1.00)
BuffName = "KSanteW"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "ksantewstun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "ksantewknockback", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.089, NumberOfStacks = 1, MaxStack = 1}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "KSanteW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}}
}
