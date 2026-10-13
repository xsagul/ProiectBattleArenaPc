-- auroraqrecast: written by tools/bb_write16.py from the replays (816 instances, 8 games)
--   given by the cast of AuroraQ (0.82)
--   slot 0 = AuroraQRecast while it lasts (1.00)
--   spent by the holder's hit (0.68)
--   its hit is auroraqreturnmissile (0.42)
--   its hit is aurorapassive (0.27)
BuffName = "auroraqrecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "AuroraQRecast", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "auroraqreturnmissile", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "aurorapassive", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "AuroraQ", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "auroraqreturnmissile", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.04}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
