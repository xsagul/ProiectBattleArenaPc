-- twitchdeadlyvenommarker: written by tools/bb_write16.py from the replays (5 instances, 5 games)
--   damage ticks every 1.07 s (45 ticks)
BuffName = "twitchdeadlyvenommarker"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 1.07, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "twitchdeadlyvenommarker", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "twitchdeadlyvenommarker", DamageFromData = true}}
    }}
  }}
}
