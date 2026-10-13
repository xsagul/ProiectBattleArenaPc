-- aatroxq3: written by tools/bb_write16.py from the replays (539 instances, 8 games)
--   slot 0 = AatroxQ3 while it lasts (1.00)
--   slot 48 = AatroxQWrapperCast while it lasts (1.00)
BuffName = "aatroxq3"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "AatroxQ3", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "AatroxQWrapperCast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "AatroxQ", TargetVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
