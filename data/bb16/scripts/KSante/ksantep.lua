-- ksantep: written by tools/bb_write16.py from the replays (4 instances, 4 games)
--   slot 48 = KSanteRMissile1 while it lasts (1.00)
--   slot 48 = KSanteRMissile2 while it lasts (1.00)
BuffName = "ksantep"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "KSanteRMissile1", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "KSanteRMissile2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
