-- sionpassivezombie: written by tools/bb_write16.py from the replays (29 instances, 4 games)
--   slot 0 = SionPassiveSpeed while it lasts (1.00)
--   slot 1 = SionPassiveSpeed while it lasts (1.00)
--   slot 2 = SionPassiveSpeed while it lasts (1.00)
--   slot 3 = SionPassiveSpeed while it lasts (1.00)
--   spent by the holder's hit (1.00)
--   its hit is sionpassive (0.93)
BuffName = "sionpassivezombie"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SionPassiveSpeed", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionPassiveSpeed", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SionPassiveSpeed", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "SionPassiveSpeed", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "sionpassive", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "SionQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SionE", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "SionR", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
