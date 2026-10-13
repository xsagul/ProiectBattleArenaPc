-- akshane2: written by tools/bb_write16.py from the replays (211 instances, 4 games)
--   given by the cast of AkshanE (1.00)
--   slot 2 = AkshanE2 while it lasts (1.00)
--   slot 51 = AkshanEMissile while it lasts (1.00)
BuffName = "akshane2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "AkshanE2", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 51, SlotType = ExtraSlots, SpellName = "AkshanEMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "AkshanE3", TargetVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
