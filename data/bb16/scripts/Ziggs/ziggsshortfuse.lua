-- ziggsshortfuse: written by tools/bb_write16.py from the replays (642 instances, 7 games)
--   slot 46 = ZiggsPassiveAttack while it lasts (1.00)
BuffName = "ziggsshortfuse"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ZiggsPassiveAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
