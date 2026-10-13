-- jaycepassivemeleeattack: written by tools/bb_write16.py from the replays (584 instances, 8 games)
--   slot 0 = JayceToTheSkies while it lasts (1.00)
--   slot 1 = JayceStaticField while it lasts (1.00)
--   slot 2 = JayceThunderingBlow while it lasts (1.00)
--   slot 3 = JayceStanceHtG while it lasts (1.00)
--   spent by the holder's hit (0.61)
--   its hit is jaycepassivemeleeattack (0.28)
BuffName = "jaycepassivemeleeattack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "JayceToTheSkies", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "JayceStaticField", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "JayceThunderingBlow", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "JayceStanceHtG", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaycepassivemeleeattack", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
