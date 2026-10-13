-- volibearqattack: written by tools/bb_write16.py from the replays (145 instances, 4 games)
--   slot 50 = VolibearQAttack while it lasts (1.00)
BuffName = "volibearqattack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "VolibearQAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
