-- RenektonReignOfTheTyrant: written by tools/bb_write16.py from the replays (60 instances, 7 games)
--   given by the cast of RenektonReignOfTheTyrant (0.95)
--   damage ticks every 0.54 s (1152 ticks)
BuffName = "RenektonReignOfTheTyrant"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "RenektonReignOfTheTyrant", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 15.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.54}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.54, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "RenektonReignOfTheTyrant", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "RenektonReignOfTheTyrant", DamageFromData = true}}
    }}
  }}
}
