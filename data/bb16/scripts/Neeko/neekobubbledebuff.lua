-- neekobubbledebuff: written by tools/bb_write16.py from the replays (61 instances, 3 games)
--   given when NeekoR is spent (1.00)
--   slot 46 = NeekoRDummySpell while it lasts (1.00)
BuffName = "neekobubbledebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "NeekoRDummySpell", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
