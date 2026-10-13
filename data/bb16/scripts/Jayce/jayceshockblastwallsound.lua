-- jayceshockblastwallsound: written by tools/bb_write16.py from the replays (430 instances, 8 games)
--   slot 46 = JayceShockBlastWallMis while it lasts (1.00)
BuffName = "jayceshockblastwallsound"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "JayceShockBlastWallMis", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
