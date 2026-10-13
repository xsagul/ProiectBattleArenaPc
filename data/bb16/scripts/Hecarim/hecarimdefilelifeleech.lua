-- hecarimdefilelifeleech: written by tools/bb_write16.py from the replays (3004 instances, 11 games)
--   slot 50 = HecarimWVFX while it lasts (0.96)
BuffName = "hecarimdefilelifeleech"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "HecarimWVFX", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
