-- ziggse2: written by tools/bb_write16.py from the replays (436 instances, 7 games)
--   slot 47 = ZiggsE2 while it lasts (1.00)
BuffName = "ziggse2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZiggsE2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
