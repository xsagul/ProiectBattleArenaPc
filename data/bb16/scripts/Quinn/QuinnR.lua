-- QuinnR: written by tools/bb_write16.py from the replays (176 instances, 4 games)
--   slot 3 = QuinnRReturnToQuinn while it lasts (1.00)
--   slot 3 = QuinnRFinale while it lasts (1.00)
--   spent by the holder's hit (0.80)
--   its hit is quinnrfinale (0.56)
BuffName = "QuinnR"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "QuinnRReturnToQuinn", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "QuinnRFinale", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "quinnrfinale", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "QuinnR", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "QuinnR", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
