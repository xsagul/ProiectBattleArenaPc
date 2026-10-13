-- virvoice: written by tools/bb_write16.py from the replays (20 instances, 3 games)
--   slot 46 = ViRMissile while it lasts (1.00)
BuffName = "virvoice"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ViRMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
