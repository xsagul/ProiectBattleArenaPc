-- YasuoE: written by tools/bb_write16.py from the replays (3191 instances, 20 games)
--   slot 45 = YasuoEDash while it lasts (1.00)
BuffName = "YasuoE"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "YasuoEDash", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
