-- annierburnaura: written by tools/bb_write16.py from the replays (37 instances, 3 games)
--   given when annierpen is spent (1.00)
--   given by the cast of AnnieR (0.84)
--   slot 3 = AnnieRController while it lasts (1.00)
BuffName = "annierburnaura"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AnnieRController", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AnnieR", TargetVar = "Owner"}}
}
