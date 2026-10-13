-- elisespidereenhancement: written by tools/bb_write16.py from the replays (111 instances, 7 games)
--   slot 2 = EliseSpiderEInitial while it lasts (1.00)
BuffName = "elisespidereenhancement"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderEInitial", TargetVar = "Owner"}}
}
