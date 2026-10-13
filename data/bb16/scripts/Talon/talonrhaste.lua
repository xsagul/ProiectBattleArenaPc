-- talonrhaste: written by tools/bb_write16.py from the replays (129 instances, 11 games)
--   given by the cast of TalonR (1.00)
--   slot 48 = TalonRMisOne while it lasts (1.00)
--   slot 3 = TalonRToggle while it lasts (1.00)
BuffName = "talonrhaste"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "TalonRMisOne", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "TalonRToggle", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
