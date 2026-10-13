-- PoisonTrail: written by tools/bb_write16.py from the replays (251 instances, 3 games)
--   given by the cast of PoisonTrail (1.00)
--   damage ticks every 0.27 s (15704 ticks)
BuffName = "PoisonTrail"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "PoisonTrail", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 20000.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.27}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "PoisonTrail", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "PoisonTrail", DamageFromData = true}}
    }}
  }}
}
