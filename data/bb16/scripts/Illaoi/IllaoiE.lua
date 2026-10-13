-- IllaoiE: written by tools/bb_write16.py from the replays (172 instances, 4 games)
--   given by the cast of IllaoiE (0.99)
--   slot 45 = IllaoiEMis while it lasts (1.00)
--   effect 05cf0841 at its start (1.00)
--   damage ticks every 0.53 s (650 ticks)
BuffName = "IllaoiE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "IllaoiE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 9.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.53}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "IllaoiEMis", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 97454145, BindObjectVar = "Owner", EffectIDVar = "Fx05cf0841", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.53, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "IllaoiE", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "IllaoiE", DamageFromData = true}}
    }}
  }}
}
