-- jhinpassivereload: written by tools/bb_write16.py from the replays (1000 instances, 12 games)
--   slot 46 = JhinPassiveReload while it lasts (1.00)
BuffName = "jhinpassivereload"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "JhinPassiveReload", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
