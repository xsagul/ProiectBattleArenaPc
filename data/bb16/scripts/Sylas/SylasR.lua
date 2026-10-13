-- SylasR: written by tools/bb_write16.py from the replays (196 instances, 18 games)
--   given when sylaspassiveattack is spent (0.98)
--   given when sylaspassive is spent (0.91)
--   slot 47 = SylasRCosmeticMissile while it lasts (1.00)
--   slot 0 = SylasQ while it lasts (1.00)
--   slot 1 = SylasW while it lasts (1.00)
--   slot 63 = SylasPassive while it lasts (1.00)
BuffName = "SylasR"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "SylasRCosmeticMissile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SylasQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SylasW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 63, SlotType = ExtraSlots, SpellName = "SylasPassive", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
