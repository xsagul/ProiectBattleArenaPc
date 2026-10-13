-- rengarqemp: written by tools/bb_write16.py from the replays (235 instances, 4 games)
--   slot 0 = RengarQ while it lasts (1.00)
--   slot 1 = RengarW while it lasts (1.00)
--   slot 2 = RengarE while it lasts (1.00)
--   slot 46 = RengarQEmpAttack while it lasts (1.00)
--   spent by the holder's hit (0.92)
--   its hit is rengarqemp (0.81)
BuffName = "rengarqemp"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RengarQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RengarW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RengarE", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "RengarQEmpAttack", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "rengarqemp", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
