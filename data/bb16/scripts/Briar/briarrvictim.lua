-- briarrvictim: written by tools/bb_write16.py from the replays (18 instances, 3 games)
--   slot 46 = BriarRSelf while it lasts (0.94)
BuffName = "briarrvictim"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 46, SlotType = ExtraSlots, SpellName = "BriarRSelf", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
