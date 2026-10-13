-- azirwsandsoldier: written by tools/bb_write16.py from the replays (505 instances, 3 games)
--   slot 50 = AzirWSpawnSoldier while it lasts (1.00)
BuffName = "azirwsandsoldier"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "AzirWSpawnSoldier", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
