-- udyrr2activation: written by tools/bb_write16.py from the replays (20 instances, 3 games)
--   given by the cast of UdyrR (1.00)
--   damage ticks every 0.53 s (781 ticks)
BuffName = "udyrr2activation"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.53, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "udyrr2activation", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "udyrr2activation", DamageFromData = true}}
    }}
  }}
}
