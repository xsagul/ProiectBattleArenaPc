-- VayneSilveredBolts: written by tools/bb_write16.py from the replays (8 instances, 8 games)
--   damage ticks every 9.83 s (23 ticks)
BuffName = "VayneSilveredBolts"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 9.83, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "VayneSilveredBolts", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "VayneSilveredBolts", DamageFromData = true}}
    }}
  }}
}
