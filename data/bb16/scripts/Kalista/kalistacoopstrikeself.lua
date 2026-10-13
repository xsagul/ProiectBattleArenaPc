-- kalistacoopstrikeself: written by tools/bb_write16.py from the replays (10 instances, 10 games)
--   damage ticks every 6.78 s (27 ticks)
BuffName = "kalistacoopstrikeself"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 6.78, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "kalistacoopstrikeself", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "kalistacoopstrikeself", DamageFromData = true}}
    }}
  }}
}
