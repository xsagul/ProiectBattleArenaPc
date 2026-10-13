-- kalistavornormal: written by tools/bb_write16.py from the replays (43 instances, 10 games)
--   slot 45 = KalistaRAestheticMis while it lasts (1.00)
BuffName = "kalistavornormal"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "KalistaRAestheticMis", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
