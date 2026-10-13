-- akalieendvfx: written by tools/bb_write16.py from the replays (124 instances, 7 games)
--   slot 2 = AkaliE while it lasts (1.00)
BuffName = "akalieendvfx"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "AkaliE", TargetVar = "Owner"}}
}
