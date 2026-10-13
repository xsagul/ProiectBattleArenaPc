-- neekowclone: written by tools/bb_write16.py from the replays (155 instances, 3 games)
--   given by the cast of NeekoW (1.00)
--   slot 1 = NeekoW2 while it lasts (1.00)
BuffName = "neekowclone"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "NeekoW2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "NeekoW", TargetVar = "Owner"}}
}
