-- elisespideredescenttrigger: written by tools/bb_write16.py from the replays (88 instances, 7 games)
--   slot 2 = EliseSpiderEInitial while it lasts (1.00)
BuffName = "elisespideredescenttrigger"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderEInitial", TargetVar = "Owner"}}
}
