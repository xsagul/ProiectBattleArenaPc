-- gangplankpassiveattack: written by tools/bb_write16.py from the replays (437 instances, 6 games)
--   spent by the holder's hit (0.99)
--   its hit is gangplankpassive (0.97)
BuffName = "gangplankpassiveattack"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "gangplankpassiveattackdot", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "gangplankpassive", OwnerVar = "Owner"}}
}
