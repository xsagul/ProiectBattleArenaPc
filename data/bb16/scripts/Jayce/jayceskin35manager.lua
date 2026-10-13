-- jayceskin35manager: written by tools/bb_write16.py from the replays (4 instances, 8 games)
--   slot 52 = JayceStanceGtH while it lasts (1.00)
BuffName = "jayceskin35manager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "JayceStanceGtH", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
