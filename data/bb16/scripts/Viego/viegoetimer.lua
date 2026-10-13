-- viegoetimer: written by tools/bb_write16.py from the replays (280 instances, 6 games)
--   given by the cast of ViegoE (1.00)
--   slot 49 = ViegoEMissile while it lasts (1.00)
BuffName = "viegoetimer"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "ViegoEMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
