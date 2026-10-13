-- zyraqplant: written by tools/bb_write16.py from the replays (801 instances, 4 games)
--   slot 46 = ZyraQPlant while it lasts (1.00)
BuffName = "zyraqplant"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ZyraQPlant", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
