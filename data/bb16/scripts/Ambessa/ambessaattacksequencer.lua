-- ambessaattacksequencer: written by tools/bb_write16.py from the replays (8 instances, 8 games)
--   slot 46 = AmbessaPassiveDash while it lasts (1.00)
BuffName = "ambessaattacksequencer"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "AmbessaPassiveDash", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
