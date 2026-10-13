-- rammusrknockup: written by tools/bb_write16.py from the replays (13 instances, 3 games)
--   slot 0 = PowerBall while it lasts (1.00)
BuffName = "rammusrknockup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "PowerBall", TargetVar = "Owner"}}
}
