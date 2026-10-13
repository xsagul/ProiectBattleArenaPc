-- jaycerunspeed: written by tools/bb_write16.py from the replays (8 instances, 8 games)
--   slot 52 = JayceStanceGtH while it lasts (1.00)
BuffName = "jaycerunspeed"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "JayceStanceGtH", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
