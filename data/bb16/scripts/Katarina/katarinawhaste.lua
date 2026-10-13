-- katarinawhaste: written by tools/bb_write16.py from the replays (805 instances, 14 games)
--   given by the cast of KatarinaW (1.00)
--   slot 52 = KatarinaWDaggerArc while it lasts (1.00)
BuffName = "katarinawhaste"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "KatarinaWDaggerArc", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
