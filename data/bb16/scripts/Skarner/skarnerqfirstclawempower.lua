-- skarnerqfirstclawempower: written by tools/bb_write16.py from the replays (443 instances, 5 games)
--   slot 0 = SkarnerQRockThrow while it lasts (1.00)
BuffName = "skarnerqfirstclawempower"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SkarnerQRockThrow", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SkarnerQ", TargetVar = "Owner"}}
}
