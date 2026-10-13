-- skarnerestun: written by tools/bb_write16.py from the replays (59 instances, 5 games)
--   given when SkarnerE is spent (1.00)
--   slot 2 = SkarnerE while it lasts (1.00)
BuffName = "skarnerestun"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SkarnerE", TargetVar = "Owner"}}
}
