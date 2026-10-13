-- apheliosseverummanager: written by tools/bb_write16.py from the replays (264 instances, 6 games)
--   given by the cast of ApheliosW (0.90)
--   slot 46 = ApheliosSeverumAttack while it lasts (1.00)
--   slot 0 = ApheliosSeverumQ while it lasts (1.00)
BuffName = "apheliosseverummanager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ApheliosSeverumAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ApheliosSeverumQ", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
