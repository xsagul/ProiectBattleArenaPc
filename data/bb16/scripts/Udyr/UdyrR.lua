-- UdyrR: written by tools/bb_write16.py from the replays (405 instances, 3 games)
--   given by the cast of UdyrR (1.00)
--   damage ticks every 0.37 s (3169 ticks)
BuffName = "UdyrR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "UdyrR", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.37}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "udyrractivation", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "udyrrrecastready", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.054, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "udyrr2activation", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.53}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.37, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "UdyrR", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "UdyrR", DamageFromData = true}}
    }}
  }}
}
