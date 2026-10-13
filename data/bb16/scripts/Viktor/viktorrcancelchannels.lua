-- viktorrcancelchannels: written by tools/bb_write16.py from the replays (129 instances, 10 games)
--   given by the cast of ViktorR (0.92)
--   slot 3 = ViktorRGuide while it lasts (1.00)
BuffName = "viktorrcancelchannels"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "ViktorRGuide", TargetVar = "Owner"}}
}
