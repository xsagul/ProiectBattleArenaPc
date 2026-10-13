-- azirruncyclemanager: written by tools/bb_write16.py from the replays (3 instances, 3 games)
--   slot 48 = AzirBasicAttackSoldier while it lasts (1.00)
BuffName = "azirruncyclemanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "AzirBasicAttackSoldier", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
