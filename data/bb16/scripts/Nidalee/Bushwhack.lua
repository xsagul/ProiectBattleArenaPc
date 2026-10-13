-- Bushwhack: written by tools/bb_write16.py from the replays (455 instances, 7 games)
--   given by the cast of Bushwhack (0.94)
--   damage ticks every 0.8 s (1319 ticks)
BuffName = "Bushwhack"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "Bushwhack", BuffType = BUFF_Invisibility, BuffAddType = BUFF_RENEW_EXISTING, Duration = 120.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.8}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.8, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "Bushwhack", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "Bushwhack", DamageFromData = true}}
    }}
  }}
}
