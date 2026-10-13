-- RivenFengShuiEngine: written by tools/bb_write16.py from the replays (121 instances, 12 games)
--   given by the cast of RivenFengShuiEngine (0.65)
--   slot 3 = RivenIzunaBlade while it lasts (1.00)
--   effect 02ae29d2 at its start (5.31)
--   effect 02ae29d2 gone with it (0.71)
BuffName = "RivenFengShuiEngine"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "RivenFengShuiEngine", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 15.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "rivenwindslashready", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 15.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "RivenIzunaBlade", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 44968402, BindObjectVar = "Owner", EffectIDVar = "Fx02ae29d2", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "RivenFengShuiEngine", TargetVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx02ae29d2", EffectIDVarTable = "InstanceVars"}}
}
