-- camilleedash2: written by tools/bb_write16.py from the replays (236 instances, 4 games)
--   slot 2 = CamilleE while it lasts (1.00)
BuffName = "camilleedash2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "CamilleE", TargetVar = "Owner"}}
}
