-- qiyanaq_grass_stealth_buff: written by tools/bb_write16.py from the replays (750 instances, 21 games)
--   slot 0 = QiyanaQ while it lasts (1.00)
BuffName = "qiyanaq_grass_stealth_buff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "QiyanaQ", TargetVar = "Owner"}}
}
