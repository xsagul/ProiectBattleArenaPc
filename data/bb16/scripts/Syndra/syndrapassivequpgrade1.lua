-- syndrapassivequpgrade1: written by tools/bb_write16.py from the replays (13 instances, 13 games)
--   slot 0 = SyndraQUpgrade while it lasts (1.00)
--   slot 49 = SyndraRBounce5 while it lasts (1.00)
BuffName = "syndrapassivequpgrade1"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SyndraQUpgrade", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "SyndraRBounce5", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
