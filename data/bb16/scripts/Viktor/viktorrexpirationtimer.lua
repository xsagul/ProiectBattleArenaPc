-- viktorrexpirationtimer: written by tools/bb_write16.py from the replays (88 instances, 10 games)
--   given by the cast of ViktorR (0.93)
--   slot 3 = ViktorRGuide while it lasts (1.00)
BuffName = "viktorrexpirationtimer"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ViktorRGuide", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ViktorR", TargetVar = "Owner"}}
}
