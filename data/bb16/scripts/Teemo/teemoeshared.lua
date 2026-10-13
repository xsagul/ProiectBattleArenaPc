-- teemoeshared: written by tools/bb_write16.py from the replays (5 instances, 5 games)
--   slot 45 = TeemoEAttack while it lasts (1.00)
--   slot 46 = TeemoECrit while it lasts (1.00)
BuffName = "teemoeshared"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "TeemoEAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "TeemoECrit", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
