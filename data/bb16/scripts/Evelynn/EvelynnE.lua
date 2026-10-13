-- EvelynnE: written by tools/bb_write16.py from the replays (231 instances, 5 games)
--   slot 2 = EvelynnE2 while it lasts (1.00)
BuffName = "EvelynnE"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EvelynnE2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EvelynnE", TargetVar = "Owner"}}
}
