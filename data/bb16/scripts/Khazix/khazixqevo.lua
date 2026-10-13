-- khazixqevo: written by tools/bb_write16.py from the replays (17 instances, 19 games)
--   slot 49 = KhazixQEvo while it lasts (1.00)
--   slot 0 = KhazixQLong while it lasts (1.00)
BuffName = "khazixqevo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KhazixQEvo", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "KhazixQLong", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
