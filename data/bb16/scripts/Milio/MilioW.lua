-- MilioW: written by tools/bb_write16.py from the replays (198 instances, 8 games)
--   given by the cast of MilioW (1.00)
--   slot 1 = MilioWRetarget while it lasts (1.00)
--   effect 07ef1243 at its start (1.00)
--   effect 07ef1243 gone with it (0.81)
BuffName = "MilioW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "MilioW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "MilioWRetarget", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 133108291, BindObjectVar = "Owner", EffectIDVar = "Fx07ef1243", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "MilioW", TargetVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx07ef1243", EffectIDVarTable = "InstanceVars"}}
}
