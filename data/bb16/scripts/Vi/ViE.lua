-- ViE: written by tools/bb_write16.py from the replays (305 instances, 3 games)
--   given by the cast of ViE (1.00)
--   slot 50 = ViEAttack while it lasts (1.00)
--   spent by the holder's hit (0.95)
--   its hit is vieattack (0.44)
--   its hit is viwmarker (0.40)
BuffName = "ViE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ViE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "ViEAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "vieattack", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "viwmarker", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
