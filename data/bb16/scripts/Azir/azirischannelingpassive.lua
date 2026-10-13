-- azirischannelingpassive: written by tools/bb_write16.py from the replays (26 instances, 3 games)
--   slot 46 = AzirTowerClickChannel while it lasts (1.00)
BuffName = "azirischannelingpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "AzirTowerClickChannel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
