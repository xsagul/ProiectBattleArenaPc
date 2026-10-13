-- apheliosp: written by tools/bb_write16.py from the replays (6 instances, 6 games)
--   slot 2 = ApheliosE while it lasts (1.00)
--   slot 46 = ApheliosSeverumAttack while it lasts (1.00)
--   slot 0 = ApheliosSeverumQ while it lasts (1.00)
--   slot 46 = ApheliosCalibrumAttack while it lasts (1.00)
--   slot 0 = ApheliosCalibrumQ while it lasts (1.00)
BuffName = "apheliosp"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "ApheliosE", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosSeverumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosSeverumQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosCalibrumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosCalibrumQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
