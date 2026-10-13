-- DariusNoxianTacticsONH: written by tools/bb_write16.py from the replays (887 instances, 9 games)
--   given by the cast of DariusNoxianTacticsONH (1.00)
--   slot 45 = DariusNoxianTacticsONHAttack while it lasts (1.00)
--   effect 07db875e at its start (3.75)
--   effect 07db875e gone with it (1.00)
--   spent by the holder's hit (0.95)
--   its hit is dariusnoxiantacticsonhattack (0.63)
BuffName = "DariusNoxianTacticsONH"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "DariusNoxianTacticsONH", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "DariusNoxianTacticsONHAttack", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 131827550, BindObjectVar = "Owner", EffectIDVar = "Fx07db875e", EffectIDVarTable = "InstanceVars"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "dariusnoxiantacticsonhattack", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx07db875e", EffectIDVarTable = "InstanceVars"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "dariusnoxiantacticsslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
