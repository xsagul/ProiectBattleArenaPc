-- reksaiwknockup: written by tools/bb_write16.py from the replays (245 instances, 4 games)
--   given when RekSaiW is spent (1.00)
--   given when reksaiespellpassive is spent (0.96)
--   slot 56 = RekSaiWUnburrowLockout while it lasts (1.00)
--   slot 0 = RekSaiQ while it lasts (1.00)
--   slot 1 = RekSaiW while it lasts (1.00)
--   slot 2 = RekSaiE while it lasts (1.00)
BuffName = "reksaiwknockup"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 56, SlotType = ExtraSlots, SpellName = "RekSaiWUnburrowLockout", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RekSaiQ", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "RekSaiW", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RekSaiE", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
