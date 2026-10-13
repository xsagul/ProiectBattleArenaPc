-- sylaspassiveattacknoanim: written by tools/bb_write16.py from the replays (4 instances, 18 games)
--   slot 0 = KarmaQ while it lasts (1.00)
--   slot 1 = KarmaSpiritBind while it lasts (1.00)
--   slot 2 = KarmaSolKimShield while it lasts (1.00)
BuffName = "sylaspassiveattacknoanim"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "KarmaQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "KarmaSpiritBind", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KarmaSolKimShield", TargetVar = "Owner"}}
}
