-- zoewaudioprocessing: written by tools/bb_write16.py from the replays (150 instances, 8 games)
--   slot 45 = ZoeWPassive while it lasts (1.00)
--   slot 45 = ZoeDummySpell while it lasts (1.00)
--   slot 1 = ZoeW while it lasts (0.92)
BuffName = "zoewaudioprocessing"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "ZoeWPassive", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "ZoeDummySpell", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "ZoeW", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
