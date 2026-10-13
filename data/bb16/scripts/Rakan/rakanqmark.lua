-- rakanqmark: written by tools/bb_write16.py from the replays (237 instances, 8 games)
--   slot 46 = RakanQReturnMis while it lasts (1.00)
--   effect 00079664 at its start (0.99)
BuffName = "rakanqmark"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "RakanQReturnMis", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 497252, BindObjectVar = "Owner", EffectIDVar = "Fx00079664", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
