-- renataqrecast: written by tools/bb_write16.py from the replays (129 instances, 6 games)
--   slot 0 = RenataQRecast while it lasts (1.00)
--   effect 025c2917 at its start (1.00)
--   effect 025c2917 gone with it (1.00)
BuffName = "renataqrecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RenataQRecast", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 39594263, BindObjectVar = "Owner", EffectIDVar = "Fx025c2917", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RenataQ", TargetVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx025c2917", EffectIDVarTable = "InstanceVars"}}
}
