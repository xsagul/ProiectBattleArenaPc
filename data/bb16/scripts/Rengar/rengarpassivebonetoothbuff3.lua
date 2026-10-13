-- rengarpassivebonetoothbuff3: written by tools/bb_write16.py from the replays (4 instances, 4 games)
--   slot 52 = PerkSoulFeastVisualMissile while it lasts (1.00)
--   spent by the holder's hit (0.50)
--   its hit is rengarq (0.25)
--   its hit is rengarr (0.25)
BuffName = "rengarpassivebonetoothbuff3"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "rengarq", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "rengarr", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
