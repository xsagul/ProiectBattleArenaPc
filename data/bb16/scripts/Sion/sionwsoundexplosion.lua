-- sionwsoundexplosion: written by tools/bb_write16.py from the replays (182 instances, 4 games)
--   slot 1 = SionW while it lasts (1.00)
BuffName = "sionwsoundexplosion"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionW", TargetVar = "Owner"}}
}
