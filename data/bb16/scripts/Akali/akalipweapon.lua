-- akalipweapon: written by tools/bb_write16.py from the replays (360 instances, 7 games)
--   slot 45 = AkaliPVFXMis1 while it lasts (1.00)
--   slot 45 = AkaliPVFXMis2 while it lasts (1.00)
--   slot 45 = AkaliPVFXMisEnemy1 while it lasts (1.00)
--   spent by the holder's hit (0.64)
--   its hit is akalip (0.61)
BuffName = "akalipweapon"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMis1", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMis2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMisEnemy1", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "akalip", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
