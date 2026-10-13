-- LockeR: written by tools/bb_write16.py from the replays (143 instances, 14 games)
--   slot 54 = LockeRNailMissile while it lasts (1.00)
BuffName = "LockeR"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 54, SlotType = ExtraSlots, SpellName = "LockeRNailMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
