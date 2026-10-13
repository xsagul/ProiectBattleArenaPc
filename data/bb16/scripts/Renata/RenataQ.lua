-- RenataQ: written by tools/bb_write16.py from the replays (132 instances, 6 games)
--   given when renataqselfroot is spent (1.00)
--   slot 0 = RenataQRecast while it lasts (0.98)
--   effect 025c2917 at its start (0.98)
BuffName = "RenataQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "renataqselfroot", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RenataQRecast", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 39594263, BindObjectVar = "Owner", EffectIDVar = "Fx025c2917", EffectIDVarTable = "InstanceVars"}}
}
