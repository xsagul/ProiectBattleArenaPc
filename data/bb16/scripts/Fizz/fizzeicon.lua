-- fizzeicon: written by tools/bb_write16.py from the replays (487 instances, 6 games)
--   given by the cast of FizzE (1.00)
--   slot 2 = FizzEBuffer while it lasts (1.00)
BuffName = "fizzeicon"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "FizzEBuffer", TargetVar = "Owner"}}
}
