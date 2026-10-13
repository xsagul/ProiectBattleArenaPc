-- LeblancW: written by tools/bb_write16.py from the replays (842 instances, 8 games)
--   given by the cast of LeblancW (1.00)
--   slot 1 = LeblancWReturn while it lasts (1.00)
--   slot 3 = LeblancRW while it lasts (0.99)
BuffName = "LeblancW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "LeblancW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "LeblancWReturn", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "LeblancRW", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "LeblancW", TargetVar = "Owner"}}
}
