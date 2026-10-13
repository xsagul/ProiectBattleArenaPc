-- MalzaharR: written by tools/bb_write16.py from the replays (39 instances, 4 games)
--   given by the cast of MalzaharR (0.97)
--   damage ticks every 0.21 s (408 ticks)
BuffName = "MalzaharR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "malzaharrsound", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "MalzaharR", BuffType = BUFF_Suppression, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.25, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.21}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "globaltruesight", BuffType = BUFF_CombatDehancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.21, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "MalzaharR", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "MalzaharR", DamageFromData = true}}
    }}
  }}
}
