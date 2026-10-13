-- NetherBlade: written by tools/bb_write16.py from the replays (514 instances, 7 games)
--   given by the cast of NetherBlade (1.00)
--   spent by the holder's hit (0.87)
--   its hit is netherbladebuff (0.84)
BuffName = "NetherBlade"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "NetherBlade", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "netherbladebuff", OwnerVar = "Owner"}}
}
