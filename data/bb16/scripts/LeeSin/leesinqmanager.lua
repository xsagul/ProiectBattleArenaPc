-- leesinqmanager: written by tools/bb_write16.py from the replays (873 instances, 9 games)
--   slot 0 = LeeSinQTwo while it lasts (1.00)
BuffName = "leesinqmanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "LeeSinQTwo", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "LeeSinQOne", TargetVar = "Owner"}}
}
