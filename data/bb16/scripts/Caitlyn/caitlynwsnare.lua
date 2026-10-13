-- caitlynwsnare: written by tools/bb_write16.py from the replays (106 instances, 9 games)
--   slot 50 = CaitlynWSnare while it lasts (1.00)
BuffName = "caitlynwsnare"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "CaitlynWSnare", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
