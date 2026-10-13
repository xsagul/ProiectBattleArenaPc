-- ksanteq3: written by tools/bb_write16.py from the replays (341 instances, 4 games)
--   slot 0 = KSanteQ3 while it lasts (1.00)
BuffName = "ksanteq3"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "KSanteQ3", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "KSanteQ", TargetVar = "Owner"}}
}
