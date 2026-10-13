-- leblancrqmark: written by tools/bb_write16.py from the replays (33 instances, 8 games)
--   slot 52 = LeblancQDetonate while it lasts (0.94)
BuffName = "leblancrqmark"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "LeblancQDetonate", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
