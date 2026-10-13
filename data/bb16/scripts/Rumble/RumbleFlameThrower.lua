-- RumbleFlameThrower: written by tools/bb_write16.py from the replays (444 instances, 3 games)
--   given by the cast of RumbleFlameThrower (0.66)
--   damage ticks every 0.27 s (6717 ticks)
BuffName = "RumbleFlameThrower"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "RumbleFlameThrower", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.35, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.27}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "RumbleFlameThrower", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "RumbleFlameThrower", DamageFromData = true}}
    }}
  }}
}
