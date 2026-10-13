-- powerballstun: written by tools/bb_write16.py from the replays (209 instances, 3 games)
--   given when PowerBall is spent (0.98)
--   slot 0 = PowerBall while it lasts (0.98)
BuffName = "powerballstun"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "PowerBall", TargetVar = "Owner"}}
}
