-- zaahenq2: written by tools/bb_write16.py from the replays (381 instances, 6 games)
--   slot 47 = ZaahenQ2Attack while it lasts (1.00)
--   spent by the holder's hit (0.90)
--   its hit is zaahenq2attack (0.28)
BuffName = "zaahenq2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZaahenQ2Attack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "zaahenq2attack", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "zaahenqknockup", BuffType = BUFF_Knockup, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.75, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
