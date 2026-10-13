-- kaisaqevolved: written by tools/bb_write16.py from the replays (13 instances, 14 games)
--   slot 49 = KaisaQEvolved while it lasts (1.00)
BuffName = "kaisaqevolved"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KaisaQEvolved", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
