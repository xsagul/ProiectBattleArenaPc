-- apheliosinfernummanager: written by tools/bb_write16.py from the replays (252 instances, 6 games)
--   given by the cast of ApheliosW (0.89)
--   slot 46 = ApheliosInfernumAttack while it lasts (1.00)
--   slot 0 = ApheliosInfernumQ while it lasts (1.00)
BuffName = "apheliosinfernummanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosInfernumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosInfernumQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
