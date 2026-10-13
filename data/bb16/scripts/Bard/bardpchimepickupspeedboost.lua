-- bardpchimepickupspeedboost: written by tools/bb_write16.py from the replays (116 instances, 4 games)
--   slot 56 = BardPChimePickupLinesMissile while it lasts (1.00)
BuffName = "bardpchimepickupspeedboost"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 56, SlotType = ExtraSlots, SpellName = "BardPChimePickupLinesMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
