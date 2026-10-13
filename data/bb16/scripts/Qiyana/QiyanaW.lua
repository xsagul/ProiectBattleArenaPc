-- QiyanaW: written by tools/bb_write16.py from the replays (21 instances, 21 games)
--   damage ticks every 1.27 s (552 ticks)
BuffName = "QiyanaW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "qiyanawenchantedbuff", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "qiyanaq_rock", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2500.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "qiyanaq_grass", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2500.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "qiyanaq_water", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2500.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 1.27, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "QiyanaW", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "QiyanaW", DamageFromData = true}}
    }}
  }}
}
