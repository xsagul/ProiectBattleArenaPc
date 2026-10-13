-- apheliosgravitummanager: written by tools/bb_write16.py from the replays (222 instances, 6 games)
--   given by the cast of ApheliosW (0.88)
--   slot 46 = ApheliosGravitumAttack while it lasts (1.00)
--   slot 0 = ApheliosGravitumQ while it lasts (1.00)
BuffName = "apheliosgravitummanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosGravitumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosGravitumQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
