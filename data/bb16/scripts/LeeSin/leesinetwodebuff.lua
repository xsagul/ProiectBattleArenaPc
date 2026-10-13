-- leesinetwodebuff: written by tools/bb_write16.py from the replays (1137 instances, 9 games)
--   given when leesinemanager is spent (1.00)
--   slot 2 = LeeSinEOne while it lasts (1.00)
BuffName = "leesinetwodebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "LeeSinEOne", TargetVar = "Owner"}}
}
