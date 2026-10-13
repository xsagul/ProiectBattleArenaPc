-- SwainW: written by tools/bb_write16.py from the replays (87 instances, 5 games)
--   slot 48 = SwainPSoulTrail while it lasts (1.00)
BuffName = "SwainW"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "SwainPSoulTrail", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
