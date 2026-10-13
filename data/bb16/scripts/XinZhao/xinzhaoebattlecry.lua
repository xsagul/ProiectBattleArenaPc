-- xinzhaoebattlecry: written by tools/bb_write16.py from the replays (416 instances, 4 games)
--   slot 49 = XinZhaoESpellCastTrigger while it lasts (1.00)
--   slot 48 = XinZhaoEDash while it lasts (0.91)
--   effect 0dc76864 at its start (1.01)
BuffName = "xinzhaoebattlecry"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "XinZhaoESpellCastTrigger", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "XinZhaoEDash", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 231172196, BindObjectVar = "Owner", EffectIDVar = "Fx0dc76864", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
