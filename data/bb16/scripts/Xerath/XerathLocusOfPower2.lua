-- XerathLocusOfPower2: written by tools/bb_write16.py from the replays (56 instances, 7 games)
--   given by the cast of XerathLocusOfPower2 (1.00)
--   slot 3 = XerathRMissileWrapper while it lasts (1.00)
BuffName = "XerathLocusOfPower2"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "XerathLocusOfPower2", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "xerathrshots", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "XerathRMissileWrapper", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "XerathLocusOfPower2", TargetVar = "Owner"}}
}
