-- yuumiphealmark: written by tools/bb_write16.py from the replays (13 instances, 6 games)
--   slot 45 = YuumiPHealMis while it lasts (1.00)
--   effect 04afea23 at its start (1.00)
--   effect 007a7ff6 at its start (1.00)
BuffName = "yuumiphealmark"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "YuumiPHealMis", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 8028150, BindObjectVar = "Owner", EffectIDVar = "Fx007a7ff6", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
