-- HeimerdingerR: written by tools/bb_write16.py from the replays (36 instances, 3 games)
--   given by the cast of HeimerdingerR (1.00)
--   slot 0 = HeimerdingerQUlt while it lasts (1.00)
--   slot 1 = HeimerdingerWUlt while it lasts (1.00)
--   slot 2 = HeimerdingerEUlt while it lasts (1.00)
--   effect 0f4b7531 at its start (1.00)
--   effect 0f4b7531 gone with it (1.00)
BuffName = "HeimerdingerR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "HeimerdingerR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "HeimerdingerQUlt", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "HeimerdingerWUlt", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "HeimerdingerEUlt", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 256603441, BindObjectVar = "Owner", EffectIDVar = "Fx0f4b7531", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "HeimerdingerQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "HeimerdingerW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "HeimerdingerE", TargetVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx0f4b7531", EffectIDVarTable = "InstanceVars"}}
}
