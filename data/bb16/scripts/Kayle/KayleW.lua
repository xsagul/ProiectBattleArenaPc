-- KayleW: written by tools/bb_write16.py from the replays (373 instances, 6 games)
--   given by the cast of KayleW (0.99)
--   slot 47 = KayleWHeal while it lasts (0.99)
--   effect 0ac0f283 at its start (1.48)
BuffName = "KayleW"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "KayleWHeal", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
