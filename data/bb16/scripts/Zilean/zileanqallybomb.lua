-- zileanqallybomb: written by tools/bb_write16.py from the replays (75 instances, 7 games)
--   slot 46 = ZileanQAttachAudio while it lasts (1.00)
BuffName = "zileanqallybomb"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "ZileanQAttachAudio", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
