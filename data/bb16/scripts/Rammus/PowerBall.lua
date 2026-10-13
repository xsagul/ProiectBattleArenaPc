-- PowerBall: written by tools/bb_write16.py from the replays (227 instances, 3 games)
--   given by the cast of PowerBall (1.00)
--   slot 0 = PowerBallCancel while it lasts (1.00)
BuffName = "PowerBall"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "PowerBall", BuffType = BUFF_Haste, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "PowerBallCancel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "PowerBall", TargetVar = "Owner"}}
}
