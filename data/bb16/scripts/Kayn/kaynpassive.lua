-- kaynpassive: written by tools/bb_write16.py from the replays (18 instances, 18 games)
--   slot 63 = KaynPassive while it lasts (1.00)
BuffName = "kaynpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 63, SlotType = ExtraSlots, SpellName = "KaynPassive", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
