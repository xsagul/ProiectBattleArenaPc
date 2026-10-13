-- UrgotW: written by tools/bb_write16.py from the replays (691 instances, 3 games)
--   given by the cast of UrgotW (1.00)
--   slot 1 = UrgotWCancel while it lasts (1.00)
BuffName = "UrgotW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "UrgotW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25002.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "UrgotWCancel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "UrgotW", TargetVar = "Owner"}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "srt_2024_horde_dot_buff", BuffType = BUFF_Damage, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.6, NumberOfStacks = 1, MaxStack = 1}}
}
