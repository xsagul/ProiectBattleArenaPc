-- BelvethE: written by tools/bb_write16.py from the replays (153 instances, 4 games)
--   given by the cast of BelvethE (1.00)
--   damage ticks every 0.16 s (858 ticks)
BuffName = "BelvethE"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "BelvethE", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.16}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.16, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "BelvethE", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "BelvethE", DamageFromData = true}}
    }}
  }}
}
