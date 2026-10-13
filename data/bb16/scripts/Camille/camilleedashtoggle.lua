-- camilleedashtoggle: written by tools/bb_write16.py from the replays (240 instances, 4 games)
--   slot 2 = CamilleEDash2 while it lasts (1.00)
BuffName = "camilleedashtoggle"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "CamilleEDash2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "CamilleE", TargetVar = "Owner"}}
}
