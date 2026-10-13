-- CassiopeiaQ: written by tools/bb_write16.py from the replays (291 instances, 6 games)
--   damage ticks every 0.53 s (2123 ticks)
BuffName = "CassiopeiaQ"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.53, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "CassiopeiaQ", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "CassiopeiaQ", DamageFromData = true}}
    }}
  }}
}
