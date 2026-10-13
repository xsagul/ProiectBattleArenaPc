-- auroraqreturnmissile: written by tools/bb_write16.py from the replays (1770 instances, 8 games)
--   given when auroraqrecast is spent (0.89)
--   slot 51 = AuroraQReturnMissile while it lasts (0.90)
--   damage ticks every 0.04 s (5000 ticks)
BuffName = "auroraqreturnmissile"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 51, SlotType = ExtraSlots, SpellName = "AuroraQReturnMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnUpdateActionsBuildingBlocks = {
  {Function = BBExecutePeriodically, Params = {TimeBetweenExecutions = 0.04, TrackTimeVar = "LastTick", TrackTimeVarTable = "InstanceVars", ExecuteImmediately = false}, SubBlocks = {
    {Function = BBForEachUnitInTargetArea, Params = {AttackerVar = "Owner", CenterVar = "Owner", RangeFromData = "auroraqreturnmissile", Flags = "AffectEnemies AffectNeutral AffectMinions AffectHeroes", IteratorVar = "Unit"}, SubBlocks = {
      {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Unit", SpellName = "auroraqreturnmissile", DamageFromData = true}}
    }}
  }}
}
