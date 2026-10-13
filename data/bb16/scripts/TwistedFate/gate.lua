-- gate: written by tools/bb_write16.py from the replays (42 instances, 7 games)
--   slot 3 = Destiny while it lasts (1.00)
BuffName = "gate"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "Destiny", TargetVar = "Owner"}}
}
