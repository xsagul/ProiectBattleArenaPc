-- kaynskin20manager: written by tools/bb_write16.py from the replays (4 instances, 18 games)
--   slot 63 = KaynPassive while it lasts (1.00)
BuffName = "kaynskin20manager"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 63, SlotType = ExtraSlots, SpellName = "KaynPassive", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
