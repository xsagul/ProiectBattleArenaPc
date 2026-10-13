-- ZoeQ: written by tools/bb_write16.py from the replays (825 instances, 8 games)
--   slot 47 = ZoeQMissile while it lasts (1.00)
--   slot 0 = ZoeQRecast while it lasts (1.00)
BuffName = "ZoeQ"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "ZoeQMissile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ZoeQRecast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ZoeQ", TargetVar = "Owner"}}
}
