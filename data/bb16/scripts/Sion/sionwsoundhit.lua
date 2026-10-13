-- sionwsoundhit: written by tools/bb_write16.py from the replays (300 instances, 4 games)
--   given when sionwshieldstacks is spent (1.00)
--   slot 1 = SionW while it lasts (1.00)
BuffName = "sionwsoundhit"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionW", TargetVar = "Owner"}}
}
