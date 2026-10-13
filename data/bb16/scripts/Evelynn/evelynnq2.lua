-- evelynnq2: written by tools/bb_write16.py from the replays (812 instances, 5 games)
--   slot 0 = EvelynnQ2 while it lasts (1.00)
BuffName = "evelynnq2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "EvelynnQ2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "EvelynnQ", TargetVar = "Owner"}}
}
