-- braumwdash: written by tools/bb_write16.py from the replays (188 instances, 7 games)
--   slot 46 = BraumWDummySpell while it lasts (1.00)
BuffName = "braumwdash"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "BraumWDummySpell", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
