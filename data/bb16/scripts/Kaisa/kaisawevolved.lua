-- kaisawevolved: written by tools/bb_write16.py from the replays (6 instances, 14 games)
--   slot 49 = KaisaWEvolved while it lasts (1.00)
BuffName = "kaisawevolved"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KaisaWEvolved", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
