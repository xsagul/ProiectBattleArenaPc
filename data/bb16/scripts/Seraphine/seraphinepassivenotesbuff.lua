-- seraphinepassivenotesbuff: written by tools/bb_write16.py from the replays (948 instances, 4 games)
--   slot 52 = SeraphinePassiveNotesMissileOrbitingAlly while it lasts (0.98)
BuffName = "seraphinepassivenotesbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphinePassiveNotesMissileOrbitingAlly", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
