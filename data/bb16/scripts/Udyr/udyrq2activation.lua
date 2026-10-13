-- udyrq2activation: written by tools/bb_write16.py from the replays (89 instances, 3 games)
--   given by the cast of UdyrQ (1.00)
--   damage ticks every 0.2 s (968 ticks)
BuffName = "udyrq2activation"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.2, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "udyrq2activation", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "udyrq2activation", DamageFromData = true}}
    }}
  }}
}
