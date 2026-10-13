-- hecarimultsound: written by tools/bb_write16.py from the replays (116 instances, 11 games)
--   given by the cast of HecarimUlt (0.97)
--   slot 47 = HecarimUltCharge while it lasts (1.00)
--   slot 49 = HecarimUltMissile while it lasts (1.00)
BuffName = "hecarimultsound"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "HecarimUltCharge", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 49, SlotType = ExtraSlots, SpellName = "HecarimUltMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
