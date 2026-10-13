-- shacortinybox: written by tools/bb_write16.py from the replays (258 instances, 8 games)
--   given when hallucinateguide is spent (1.00)
--   slot 3 = HallucinateFull while it lasts (1.00)
BuffName = "shacortinybox"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "HallucinateFull", TargetVar = "Owner"}}
}
