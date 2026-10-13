-- GwenQ: written by tools/bb_write16.py from the replays (514 instances, 4 games)
--   spent by the holder's hit (0.59)
--   its hit is gwenq (0.55)
--   damage ticks every 0.07 s (6917 ticks)
BuffName = "GwenQ"
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "gwenqtarstackcounter", BuffType = BUFF_Counter, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "gwenq", OwnerVar = "Owner"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.07, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "GwenQ", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "GwenQ", DamageFromData = true}}
    }}
  }}
}
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "gwenz_lockfacing", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.5, NumberOfStacks = 1, MaxStack = 1}}
}
