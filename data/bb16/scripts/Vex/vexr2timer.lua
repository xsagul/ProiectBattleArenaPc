-- vexr2timer: written by tools/bb_write16.py from the replays (57 instances, 5 games)
--   slot 3 = VexR2 while it lasts (1.00)
--   effect 04afea23 at its start (1.02)
--   effect 04afea23 gone with it (0.98)
BuffName = "vexr2timer"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "VexR2", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "VexR", TargetVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
