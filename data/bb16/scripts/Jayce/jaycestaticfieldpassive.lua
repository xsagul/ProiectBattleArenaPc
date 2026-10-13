-- jaycestaticfieldpassive: written by tools/bb_write16.py from the replays (578 instances, 8 games)
--   slot 0 = JayceToTheSkies while it lasts (0.98)
--   slot 1 = JayceStaticField while it lasts (0.98)
--   slot 2 = JayceThunderingBlow while it lasts (0.98)
--   slot 3 = JayceStanceHtG while it lasts (0.98)
BuffName = "jaycestaticfieldpassive"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "JayceToTheSkies", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "JayceStaticField", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "JayceThunderingBlow", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "JayceStanceHtG", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "JayceShockBlast", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "JayceHyperCharge", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "JayceAccelerationGate", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "JayceStanceGtH", TargetVar = "Owner"}}
}
