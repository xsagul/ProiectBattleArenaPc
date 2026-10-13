-- leblancqdetonate: written by tools/bb_write16.py from the replays (273 instances, 8 games)
--   slot 52 = LeblancQDetonate while it lasts (1.00)
BuffName = "leblancqdetonate"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "LeblancQDetonate", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
