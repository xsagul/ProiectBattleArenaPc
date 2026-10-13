-- pantheoneresists: written by tools/bb_write16.py from the replays (42 instances, 7 games)
--   slot 45 = PantheonEShieldSlam while it lasts (1.00)
BuffName = "pantheoneresists"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "PantheonEShieldSlam", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
