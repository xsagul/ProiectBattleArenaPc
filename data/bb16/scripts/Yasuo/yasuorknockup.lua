-- yasuorknockup: written by tools/bb_write16.py from the replays (193 instances, 20 games)
--   given by the cast of YasuoR (0.99)
--   slot 54 = YasuoR_TeleportVFX_Mis while it lasts (0.98)
--   slot 49 = YasuoBasicAttack while it lasts (0.98)
--   slot 50 = YasuoCritAttack while it lasts (0.98)
--   effect 0b089c01 at its start (0.97)
BuffName = "yasuorknockup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 54, SlotType = ExtraSlots, SpellName = "YasuoR_TeleportVFX_Mis", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "YasuoBasicAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "YasuoCritAttack", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 185113601, BindObjectVar = "Owner", EffectIDVar = "Fx0b089c01", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
