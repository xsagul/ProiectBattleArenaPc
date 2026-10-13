-- gwenrrecast: written by tools/bb_write16.py from the replays (44 instances, 4 games)
--   given by the cast of GwenR (0.80)
--   slot 52 = GwenRMis while it lasts (1.00)
--   slot 52 = GwenRMis_VisualOnly while it lasts (1.00)
--   slot 3 = GwenRRecast while it lasts (1.00)
BuffName = "gwenrrecast"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "GwenRMis", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "GwenRMis_VisualOnly", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "GwenRRecast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "GwenRMis3_VisualOnly", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "GwenRMis3_VisualOnly", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "GwenR", TargetVar = "Owner"}}
}
