-- viegopassivesoul: written by tools/bb_write16.py from the replays (95 instances, 6 games)
--   slot 52 = PerkSoulFeastVisualMissile while it lasts (1.00)
BuffName = "viegopassivesoul"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
