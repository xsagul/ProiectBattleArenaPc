-- mordekaiserr_statstealenemy: written by tools/bb_write16.py from the replays (74 instances, 10 games)
--   slot 45 = MordekaiserRWispMis while it lasts (1.00)
BuffName = "mordekaiserr_statstealenemy"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "MordekaiserRWispMis", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
