-- VelkozR: written by tools/bb_write16.py from the replays (52 instances, 6 games)
--   given by the cast of VelkozR (1.00)
--   effect 063705a4 at its start (4.00)
--   effect 063705a4 gone with it (1.00)
--   damage ticks every 0.27 s (490 ticks)
BuffName = "VelkozR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "VelkozR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.85, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.27}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 104269220, BindObjectVar = "Owner", EffectIDVar = "Fx063705a4", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx063705a4", EffectIDVarTable = "InstanceVars"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "VelkozR", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "VelkozR", DamageFromData = true}}
    }}
  }}
}
