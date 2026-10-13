-- belvethpassive: written by tools/bb_write16.py from the replays (4 instances, 4 games)
--   slot 49 = BelvethBasicAttack while it lasts (1.00)
--   slot 50 = BelvethCritAttack while it lasts (1.00)
BuffName = "belvethpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "BelvethBasicAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "BelvethCritAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
