-- DefensiveBallCurl: written by tools/bb_write16.py from the replays (209 instances, 3 games)
--   given by the cast of DefensiveBallCurl (1.00)
--   slot 1 = DefensiveBallCurlCancel while it lasts (1.00)
--   damage ticks every 0.3 s (1752 ticks)
BuffName = "DefensiveBallCurl"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "DefensiveBallCurl", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 7.0, NumberOfStacks = 1, MaxStack = 1, TickRate = 0.3}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "DefensiveBallCurlCancel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "DefensiveBallCurl", TargetVar = "Owner"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.3, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "DefensiveBallCurl", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "DefensiveBallCurl", DamageFromData = true}}
    }}
  }}
}
