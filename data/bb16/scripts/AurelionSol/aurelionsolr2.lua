-- aurelionsolr2: written by tools/bb_write16.py from the replays (31 instances, 9 games)
--   slot 52 = AurelionSolR2Missile while it lasts (1.00)
BuffName = "aurelionsolr2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "AurelionSolR2Missile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
