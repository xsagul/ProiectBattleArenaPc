-- NilahR: written by tools/bb_write16.py from the replays (16 instances, 3 games)
--   given by the cast of NilahR (1.00)
--   damage ticks every 0.2 s (220 ticks)
BuffName = "NilahR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "NilahR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.2}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.2, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "NilahR", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "NilahR", DamageFromData = true}}
    }}
  }}
}
