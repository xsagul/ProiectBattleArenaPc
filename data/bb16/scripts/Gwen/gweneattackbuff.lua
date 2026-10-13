-- gweneattackbuff: written by tools/bb_write16.py from the replays (440 instances, 4 games)
--   given by the cast of GwenE (0.80)
--   slot 55 = GwenEEmpoweredAttack while it lasts (1.00)
BuffName = "gweneattackbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 55, SlotType = ExtraSlots, SpellName = "GwenEEmpoweredAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
