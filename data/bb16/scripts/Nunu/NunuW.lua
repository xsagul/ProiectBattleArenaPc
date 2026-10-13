-- NunuW: written by tools/bb_write16.py from the replays (214 instances, 4 games)
--   given by the cast of NunuW (0.98)
--   slot 58 = NunuWCircleMissile2 while it lasts (1.00)
--   slot 1 = NunuW_Recast while it lasts (0.92)
BuffName = "NunuW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "NunuW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 58, SlotType = ExtraSlots, SpellName = "NunuWCircleMissile2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "NunuW_Recast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
