-- tristanavohighburstdamage: written by tools/bb_write16.py from the replays (36 instances, 23 games)
--   slot 52 = PerkSoulFeastVisualMissile while it lasts (1.00)
BuffName = "tristanavohighburstdamage"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkSoulFeastVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
