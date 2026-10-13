-- zoewpassive: written by tools/bb_write16.py from the replays (225 instances, 8 games)
--   slot 45 = ZoeWPassive while it lasts (1.00)
BuffName = "zoewpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "ZoeWPassive", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
