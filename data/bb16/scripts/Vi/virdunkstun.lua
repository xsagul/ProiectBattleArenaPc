-- virdunkstun: written by tools/bb_write16.py from the replays (19 instances, 3 games)
--   given when ViR is spent (1.00)
--   slot 46 = ViRMissile while it lasts (1.00)
BuffName = "virdunkstun"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ViRMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
