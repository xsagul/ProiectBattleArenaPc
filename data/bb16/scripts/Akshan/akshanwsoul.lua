-- akshanwsoul: written by tools/bb_write16.py from the replays (28 instances, 4 games)
--   slot 52 = PerkPresenceOfMindVisualMissile while it lasts (1.00)
BuffName = "akshanwsoul"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "PerkPresenceOfMindVisualMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
