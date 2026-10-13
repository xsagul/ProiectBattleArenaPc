-- kennenlightningrushbuff: written by tools/bb_write16.py from the replays (935 instances, 11 games)
--   slot 2 = KennenLightningRush while it lasts (1.00)
BuffName = "kennenlightningrushbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KennenLightningRush", TargetVar = "Owner"}}
}
