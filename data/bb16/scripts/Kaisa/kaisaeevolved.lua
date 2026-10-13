-- kaisaeevolved: written by tools/bb_write16.py from the replays (12 instances, 14 games)
--   slot 49 = KaisaEEvolved while it lasts (1.00)
BuffName = "kaisaeevolved"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KaisaEEvolved", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
