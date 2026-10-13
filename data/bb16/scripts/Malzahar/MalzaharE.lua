-- MalzaharE: written by tools/bb_write16.py from the replays (1234 instances, 4 games)
--   effect 02fa3b93 at its start (0.96)
--   damage ticks every 0.27 s (7684 ticks)
BuffName = "MalzaharE"
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 49953683, BindObjectVar = "Owner", EffectIDVar = "Fx02fa3b93", EffectIDVarTable = "InstanceVars"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "MalzaharE", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "MalzaharE", DamageFromData = true}}
    }}
  }}
}
