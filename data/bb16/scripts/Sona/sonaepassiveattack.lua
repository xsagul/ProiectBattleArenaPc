-- sonaepassiveattack: written by tools/bb_write16.py from the replays (253 instances, 4 games)
--   given by the cast of SonaE (1.00)
--   slot 48 = SonaEPassiveAttack while it lasts (1.00)
BuffName = "sonaepassiveattack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "SonaEPassiveAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
