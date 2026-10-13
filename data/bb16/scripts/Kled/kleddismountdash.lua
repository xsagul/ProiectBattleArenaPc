-- kleddismountdash: written by tools/bb_write16.py from the replays (44 instances, 3 games)
--   slot 0 = KledRiderQ while it lasts (1.00)
BuffName = "kleddismountdash"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "KledRiderQ", TargetVar = "Owner"}}
}
