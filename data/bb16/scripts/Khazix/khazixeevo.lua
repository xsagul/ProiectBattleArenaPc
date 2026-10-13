-- khazixeevo: written by tools/bb_write16.py from the replays (12 instances, 19 games)
--   slot 49 = KhazixEEvo while it lasts (1.00)
--   slot 2 = KhazixELong while it lasts (1.00)
BuffName = "khazixeevo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KhazixEEvo", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KhazixELong", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
