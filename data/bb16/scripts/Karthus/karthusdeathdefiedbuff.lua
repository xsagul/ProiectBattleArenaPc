-- karthusdeathdefiedbuff: written by tools/bb_write16.py from the replays (81 instances, 9 games)
--   slot 1 = KarthusWallOfPain2 while it lasts (1.00)
--   slot 2 = KarthusDefile2 while it lasts (1.00)
--   slot 3 = KarthusFallenOne2 while it lasts (1.00)
BuffName = "karthusdeathdefiedbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "KarthusWallOfPain2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KarthusDefile2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "KarthusFallenOne2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "KarthusWallOfPain", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KarthusDefile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "KarthusFallenOne", TargetVar = "Owner"}}
}
