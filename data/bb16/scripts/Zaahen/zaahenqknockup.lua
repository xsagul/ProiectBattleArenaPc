-- zaahenqknockup: written by tools/bb_write16.py from the replays (302 instances, 6 games)
--   given when zaahenqbuff is spent (1.00)
--   given when zaahenq2 is spent (1.00)
--   slot 0 = ZaahenQ while it lasts (1.00)
BuffName = "zaahenqknockup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ZaahenQ", TargetVar = "Owner"}}
}
