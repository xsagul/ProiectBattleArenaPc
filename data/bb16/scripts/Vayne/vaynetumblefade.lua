-- vaynetumblefade: written by tools/bb_write16.py from the replays (269 instances, 8 games)
--   given by the cast of VayneTumble (1.00)
--   slot 50 = VayneTumbleUltAttack while it lasts (1.00)
BuffName = "vaynetumblefade"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "VayneTumbleUltAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
