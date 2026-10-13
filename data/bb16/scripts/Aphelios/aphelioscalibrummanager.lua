-- aphelioscalibrummanager: written by tools/bb_write16.py from the replays (329 instances, 6 games)
--   given by the cast of ApheliosW (0.91)
--   slot 46 = ApheliosCalibrumAttack while it lasts (1.00)
--   slot 0 = ApheliosCalibrumQ while it lasts (1.00)
BuffName = "aphelioscalibrummanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosCalibrumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosCalibrumQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
