-- rengarpassivebonetoothbuff5: written by tools/bb_write16.py from the replays (4 instances, 4 games)
--   slot 52 = PerkSoulFeastVisualMissile while it lasts (1.00)
BuffName = "rengarpassivebonetoothbuff5"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
