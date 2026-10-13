-- xerathqsoundbuff: written by tools/bb_write16.py from the replays (809 instances, 7 games)
--   slot 45 = XerathArcanopulse2 while it lasts (1.00)
BuffName = "xerathqsoundbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "XerathArcanopulse2", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
