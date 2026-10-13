-- DianaOrbs: written by tools/bb_write16.py from the replays (732 instances, 10 games)
--   given by the cast of DianaOrbs (1.00)
--   slot 48 = DianaOrbsMissile while it lasts (1.00)
--   spent by the holder's hit (0.86)
--   its hit is dianaorbsmissile (0.82)
BuffName = "DianaOrbs"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "dianashield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "DianaOrbs", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "DianaOrbsMissile", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "dianaorbsmissile", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
