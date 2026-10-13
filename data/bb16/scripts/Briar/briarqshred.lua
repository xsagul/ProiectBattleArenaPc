-- briarqshred: written by tools/bb_write16.py from the replays (183 instances, 3 games)
--   slot 47 = BriarQDummyCast while it lasts (1.00)
BuffName = "briarqshred"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "BriarQDummyCast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
