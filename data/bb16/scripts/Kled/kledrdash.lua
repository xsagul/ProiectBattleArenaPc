-- kledrdash: written by tools/bb_write16.py from the replays (18 instances, 3 games)
--   spent by the holder's hit (0.89)
--   its hit is kledr (0.67)
BuffName = "kledrdash"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "kledrbump", BuffType = BUFF_Knockback, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "kledr", OwnerVar = "Owner"}}
}
