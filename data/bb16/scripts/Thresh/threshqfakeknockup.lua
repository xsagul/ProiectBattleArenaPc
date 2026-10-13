-- threshqfakeknockup: written by tools/bb_write16.py from the replays (284 instances, 12 games)
--   slot 46 = ThreshQPullMissile while it lasts (1.00)
--   slot 0 = ThreshQLeap while it lasts (1.00)
--   effect 0785e844 at its start (1.00)
BuffName = "threshqfakeknockup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ThreshQPullMissile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ThreshQLeap", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 126216260, BindObjectVar = "Owner", EffectIDVar = "Fx0785e844", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
