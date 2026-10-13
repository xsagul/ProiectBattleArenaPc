-- bardqinitialtargetdebuff: written by tools/bb_write16.py from the replays (130 instances, 4 games)
--   slot 47 = BardQMissile2 while it lasts (1.00)
BuffName = "bardqinitialtargetdebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "BardQMissile2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
