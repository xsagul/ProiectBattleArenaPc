-- MonkeyKingSpinToWin: written by tools/bb_write16.py from the replays (272 instances, 14 games)
--   given by the cast of MonkeyKingSpinToWin (0.87)
--   effect 02cc8a33 at its start (1.29)
--   effect 02cc8a33 gone with it (0.85)
--   damage ticks every 0.27 s (1387 ticks)
BuffName = "MonkeyKingSpinToWin"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "monkeykingspinknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.6, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSpellEffectCreate, Params = {EffectKey = 46959155, BindObjectVar = "Owner", EffectIDVar = "Fx02cc8a33", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx02cc8a33", EffectIDVarTable = "InstanceVars"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "MonkeyKingSpinToWin", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "MonkeyKingSpinToWin", DamageFromData = true}}
    }}
  }}
}
