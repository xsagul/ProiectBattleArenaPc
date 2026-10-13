-- zoewslotactive: written by tools/bb_write16.py from the replays (185 instances, 8 games)
--   slot 45 = ZoeWVisualMissile while it lasts (1.00)
BuffName = "zoewslotactive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "ZoeWVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
