-- JaxW: written by tools/bb_write16.py from the replays (402 instances, 3 games)
--   given by the cast of JaxW (1.00)
--   spent by the holder's hit (0.92)
--   its hit is jaxwattack (0.25)
--   its hit is jaxrpassive (0.21)
BuffName = "JaxW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "JaxW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaxwattack", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaxrpassive", OwnerVar = "Owner"}}
}
