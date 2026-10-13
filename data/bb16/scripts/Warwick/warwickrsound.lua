-- warwickrsound: written by tools/bb_write16.py from the replays (21 instances, 3 games)
--   slot 48 = WarwickRChannel while it lasts (0.91)
BuffName = "warwickrsound"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "WarwickRChannel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
