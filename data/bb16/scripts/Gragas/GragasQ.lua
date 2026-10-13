-- GragasQ: written by tools/bb_write16.py from the replays (953 instances, 7 games)
--   slot 0 = GragasQToggle while it lasts (1.00)
--   spent by the holder's hit (0.68)
--   its hit is gragasq (0.66)
BuffName = "GragasQ"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "GragasQToggle", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "gragasq", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "GragasQ", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "slow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
