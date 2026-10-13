-- Destiny: written by tools/bb_write16.py from the replays (217 instances, 7 games)
--   given by the cast of Destiny (1.00)
--   slot 3 = Gate while it lasts (1.00)
BuffName = "Destiny"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "Destiny", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "Gate", TargetVar = "Owner"}}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "destiny_marker", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 8.0, NumberOfStacks = 1, MaxStack = 1}}
}
