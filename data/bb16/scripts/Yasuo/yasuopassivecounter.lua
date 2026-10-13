-- yasuopassivecounter: written by tools/bb_write16.py from the replays (20 instances, 20 games)
--   slot 49 = YasuoBasicAttack while it lasts (1.00)
--   slot 50 = YasuoCritAttack while it lasts (1.00)
BuffName = "yasuopassivecounter"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "YasuoBasicAttack", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "YasuoCritAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
