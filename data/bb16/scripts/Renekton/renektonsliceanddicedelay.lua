-- renektonsliceanddicedelay: written by tools/bb_write16.py from the replays (293 instances, 7 games)
--   given by the cast of RenektonSliceAndDice (0.85)
--   slot 2 = RenektonDice while it lasts (1.00)
--   spent by the holder's hit (0.53)
--   its hit is renektondice (0.50)
BuffName = "renektonsliceanddicedelay"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RenektonDice", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "renektondice", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "RenektonSliceAndDice", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
