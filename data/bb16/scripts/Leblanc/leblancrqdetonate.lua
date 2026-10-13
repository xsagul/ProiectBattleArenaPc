-- leblancrqdetonate: written by tools/bb_write16.py from the replays (17 instances, 8 games)
--   slot 52 = LeblancRQDetonate while it lasts (1.00)
BuffName = "leblancrqdetonate"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "LeblancRQDetonate", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
