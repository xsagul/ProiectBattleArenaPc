-- samirapjuggle: written by tools/bb_write16.py from the replays (38 instances, 4 games)
--   slot 55 = SamiraPJuggle while it lasts (1.00)
--   slot 46 = SamiraPMissileOffhand while it lasts (1.00)
BuffName = "samirapjuggle"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 55, SlotType = ExtraSlots, SpellName = "SamiraPJuggle", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "SamiraPMissileOffhand", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "SamiraPMissile", TargetVar = "Owner"}}
}
