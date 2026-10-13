-- KaynR: written by tools/bb_write16.py from the replays (163 instances, 18 games)
--   given by the cast of KaynR (1.00)
--   spent by the holder's hit (0.83)
--   its hit is kaynr (0.40)
--   its hit is kaynpassive (0.27)
BuffName = "KaynR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "KaynR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "kaynr", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "kaynpassive", OwnerVar = "Owner"}}
}
