-- AkaliR: written by tools/bb_write16.py from the replays (59 instances, 7 games)
--   given by the cast of AkaliR (0.98)
--   slot 3 = AkaliRb while it lasts (1.00)
BuffName = "AkaliR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AkaliR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AkaliRb", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AkaliR", TargetVar = "Owner"}}
}
