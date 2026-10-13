-- samirapswordjuggle: written by tools/bb_write16.py from the replays (9 instances, 4 games)
--   slot 55 = SamiraPSwordJuggle while it lasts (1.00)
BuffName = "samirapswordjuggle"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 55, SlotType = ExtraSlots, SpellName = "SamiraPSwordJuggle", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
