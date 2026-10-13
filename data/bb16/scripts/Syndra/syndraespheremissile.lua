-- syndraespheremissile: written by tools/bb_write16.py from the replays (751 instances, 13 games)
--   slot 50 = SyndraESphereMissile while it lasts (1.00)
BuffName = "syndraespheremissile"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "SyndraESphereMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
