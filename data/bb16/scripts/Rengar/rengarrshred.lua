-- rengarrshred: written by tools/bb_write16.py from the replays (41 instances, 4 games)
--   slot 50 = RengarPassiveAttack while it lasts (1.00)
BuffName = "rengarrshred"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "RengarPassiveAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
