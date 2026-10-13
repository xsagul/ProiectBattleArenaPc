-- sylaspassiveattack: written by tools/bb_write16.py from the replays (3947 instances, 18 games)
--   spent by the holder's hit (0.65)
--   its hit is sylaspassive (0.39)
BuffName = "sylaspassiveattack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "SylasR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 218.182, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "sylaspassive", OwnerVar = "Owner"}}
}
