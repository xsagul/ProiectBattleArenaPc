-- zyraeplant: written by tools/bb_write16.py from the replays (213 instances, 4 games)
--   slot 47 = ZyraEPlant while it lasts (1.00)
BuffName = "zyraeplant"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZyraEPlant", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
