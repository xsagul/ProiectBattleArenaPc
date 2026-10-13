-- aurelionsolrannouncement: written by tools/bb_write16.py from the replays (32 instances, 9 games)
--   slot 3 = AurelionSolR2 while it lasts (1.00)
--   spent by the holder's hit (0.68)
--   its hit is aurelionsolr2missile (0.55)
BuffName = "aurelionsolrannouncement"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AurelionSolR2", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "aurelionsolr2missile", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AurelionSolR", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "aurelionsolr2knockupdebuff", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
