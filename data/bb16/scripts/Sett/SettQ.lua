-- SettQ: written by tools/bb_write16.py from the replays (404 instances, 4 games)
--   given by the cast of SettQ (0.99)
--   slot 45 = SettQAttack while it lasts (1.00)
--   spent by the holder's hit (0.73)
--   its hit is settqattack2 (0.42)
BuffName = "SettQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "SettQ", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "settqmsbuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "SettQAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "settqattack2", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
