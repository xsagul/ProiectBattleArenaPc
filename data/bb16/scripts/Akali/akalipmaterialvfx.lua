-- akalipmaterialvfx: written by tools/bb_write16.py from the replays (360 instances, 7 games)
--   slot 45 = AkaliPVFXMis1 while it lasts (1.00)
--   slot 45 = AkaliPVFXMis2 while it lasts (1.00)
--   slot 45 = AkaliPVFXMisEnemy1 while it lasts (1.00)
BuffName = "akalipmaterialvfx"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMis1", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMis2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "AkaliPVFXMisEnemy1", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
