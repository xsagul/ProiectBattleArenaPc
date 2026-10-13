-- ShenQ: written by tools/bb_write16.py from the replays (12 instances, 12 games)
--   damage ticks every 1.97 s (74 ticks)
BuffName = "ShenQ"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "shenqtransmitter", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 30.0, NumberOfStacks = 1, MaxStack = 1}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "shenqslow", BuffType = BUFF_Slow, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 1.97, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "ShenQ", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "ShenQ", DamageFromData = true}}
    }}
  }}
}
