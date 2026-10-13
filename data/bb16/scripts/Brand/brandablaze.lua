-- brandablaze: Blaze passive dot
BuffName = "brandablaze"
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 1.0, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBApplyDamage, Params = {AttackerVar = "Caster", TargetVar = "Owner", SpellName = "brandpassive", Damage = 25.0, DamageType = MAGIC_DAMAGE}}
  }}
}
