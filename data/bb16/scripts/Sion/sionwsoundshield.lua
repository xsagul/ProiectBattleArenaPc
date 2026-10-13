-- sionwsoundshield: written by tools/bb_write16.py from the replays (182 instances, 4 games)
--   given by the cast of SionW (1.00)
--   slot 1 = SionWDetonate while it lasts (1.00)
BuffName = "sionwsoundshield"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionWDetonate", TargetVar = "Owner"}}
}
