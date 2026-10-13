-- kindredmarkofthekindredstackcounter: written by tools/bb_write16.py from the replays (4 instances, 4 games)
--   slot 48 = KindredBasicAttack while it lasts (1.00)
BuffName = "kindredmarkofthekindredstackcounter"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "KindredBasicAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
