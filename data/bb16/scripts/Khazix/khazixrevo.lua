-- khazixrevo: written by tools/bb_write16.py from the replays (12 instances, 19 games)
--   slot 49 = KhazixREvo while it lasts (1.00)
BuffName = "khazixrevo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "KhazixREvo", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
