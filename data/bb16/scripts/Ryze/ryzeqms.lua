-- ryzeqms: written by tools/bb_write16.py from the replays (69 instances, 3 games)
--   given by the cast of RyzeQWrapper (1.00)
--   slot 49 = RyzeQ while it lasts (1.00)
--   effect 0ac0f283 at its start (1.00)
--   effect 0ac0f283 gone with it (1.00)
BuffName = "ryzeqms"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "RyzeQ", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
