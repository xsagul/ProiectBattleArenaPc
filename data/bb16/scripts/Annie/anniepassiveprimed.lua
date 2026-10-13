-- anniepassiveprimed: written by tools/bb_write16.py from the replays (171 instances, 3 games)
--   spent by the holder's hit (0.88)
--   its hit is annieq (0.51)
--   its hit is anniew (0.22)
BuffName = "anniepassiveprimed"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "stun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "anniepassivestun", BuffType = BUFF_Stun, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "annieq", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "anniew", OwnerVar = "Owner"}}
}
