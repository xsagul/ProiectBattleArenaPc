-- dravenrdoublecast: written by tools/bb_write16.py from the replays (100 instances, 11 games)
--   slot 46 = DravenR while it lasts (1.00)
--   slot 3 = DravenRDoublecast while it lasts (1.00)
--   spent by the holder's hit (0.76)
--   its hit is dravenr (0.72)
BuffName = "dravenrdoublecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "DravenR", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "DravenRDoublecast", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "dravenr", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "DravenRCast", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
