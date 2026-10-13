-- rengarpassiveempoweredms: written by tools/bb_write16.py from the replays (319 instances, 4 games)
--   slot 0 = RengarQ while it lasts (1.00)
--   slot 1 = RengarW while it lasts (1.00)
--   slot 2 = RengarE while it lasts (1.00)
BuffName = "rengarpassiveempoweredms"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RengarQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RengarW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RengarE", TargetVar = "Owner"}}
}
