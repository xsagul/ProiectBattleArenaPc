-- gatlingdebuff: written by tools/bb_write16.py from the replays (1313 instances, 9 games)
--   slot 45 = GGSpray while it lasts (1.00)
BuffName = "gatlingdebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "GGSpray", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
