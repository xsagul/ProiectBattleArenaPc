-- neekor2: written by tools/bb_write16.py from the replays (26 instances, 3 games)
--   slot 46 = NeekoRDummySpell while it lasts (1.00)
BuffName = "neekor2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "NeekoRDummySpell", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
