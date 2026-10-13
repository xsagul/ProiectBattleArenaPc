-- HecarimW: written by tools/bb_write16.py from the replays (927 instances, 11 games)
--   given by the cast of HecarimW (1.00)
--   effect 0725e844 at its start (1.00)
--   damage ticks every 0.53 s (12191 ticks)
BuffName = "HecarimW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "HecarimW", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 4.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.53}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 119924804, BindObjectVar = "Owner", EffectIDVar = "Fx0725e844", EffectIDVarTable = "InstanceVars"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.53, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "HecarimW", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "HecarimW", DamageFromData = true}}
    }}
  }}
}
