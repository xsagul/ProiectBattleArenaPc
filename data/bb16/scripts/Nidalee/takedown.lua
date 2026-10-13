-- takedown: written by tools/bb_write16.py from the replays (738 instances, 7 games)
--   slot 45 = NidaleeTakedownAttack while it lasts (1.00)
--   spent by the holder's hit (0.93)
--   its hit is nidaleetakedownattack (0.56)
BuffName = "takedown"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "NidaleeTakedownAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "nidaleetakedownattack", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
