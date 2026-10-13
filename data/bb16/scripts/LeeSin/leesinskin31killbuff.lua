-- leesinskin31killbuff: written by tools/bb_write16.py from the replays (21 instances, 9 games)
--   slot 52 = PerkSoulFeastVisualMissile while it lasts (1.00)
BuffName = "leesinskin31killbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
