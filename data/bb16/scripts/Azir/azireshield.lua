-- azireshield: written by tools/bb_write16.py from the replays (74 instances, 3 games)
--   given by the cast of AzirEWrapper (0.76)
--   slot 46 = AzirE while it lasts (1.00)
BuffName = "azireshield"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "AzirE", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
