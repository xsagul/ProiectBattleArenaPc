-- maokaiqknockback: written by tools/bb_write16.py from the replays (173 instances, 3 games)
--   slot 45 = MaokaiQMissile while it lasts (1.00)
BuffName = "maokaiqknockback"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "MaokaiQMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
