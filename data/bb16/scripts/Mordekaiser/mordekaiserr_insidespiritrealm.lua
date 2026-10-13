-- mordekaiserr_insidespiritrealm: written by tools/bb_write16.py from the replays (148 instances, 10 games)
--   slot 45 = MordekaiserRWispMis while it lasts (1.00)
BuffName = "mordekaiserr_insidespiritrealm"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "MordekaiserRWispMis", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
