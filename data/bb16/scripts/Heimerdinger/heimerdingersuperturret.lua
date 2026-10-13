-- heimerdingersuperturret: written by tools/bb_write16.py from the replays (14 instances, 3 games)
--   given when HeimerdingerR is spent (1.00)
--   slot 0 = HeimerdingerQ while it lasts (1.00)
--   slot 1 = HeimerdingerW while it lasts (1.00)
--   slot 2 = HeimerdingerE while it lasts (1.00)
BuffName = "heimerdingersuperturret"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "HeimerdingerQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "HeimerdingerW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "HeimerdingerE", TargetVar = "Owner"}}
}
