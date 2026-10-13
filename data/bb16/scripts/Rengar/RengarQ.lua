-- RengarQ: written by tools/bb_write16.py from the replays (612 instances, 4 games)
--   given by the cast of RengarQ (0.98)
--   slot 46 = RengarQAttack while it lasts (1.00)
--   spent by the holder's hit (0.88)
--   its hit is rengarq (0.79)
BuffName = "RengarQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "RengarQ", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "rengarqasbuff", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "RengarQAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "rengarq", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
