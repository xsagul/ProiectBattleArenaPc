-- SkarnerE: written by tools/bb_write16.py from the replays (169 instances, 5 games)
--   given by the cast of SkarnerE (0.99)
--   slot 2 = SkarnerECancel while it lasts (1.00)
BuffName = "SkarnerE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "SkarnerE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.75, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SkarnerECancel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SkarnerE", TargetVar = "Owner"}}
}
