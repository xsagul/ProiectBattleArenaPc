-- elisespidere: written by tools/bb_write16.py from the replays (111 instances, 7 games)
--   slot 2 = EliseSpiderE while it lasts (1.00)
--   slot 2 = EliseSpiderEDescent while it lasts (1.00)
BuffName = "elisespidere"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderE", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderEDescent", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderEInitial", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "EliseSpiderEInitial", TargetVar = "Owner"}}
}
