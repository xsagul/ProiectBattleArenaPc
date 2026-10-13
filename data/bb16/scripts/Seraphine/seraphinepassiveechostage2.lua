-- seraphinepassiveechostage2: written by tools/bb_write16.py from the replays (275 instances, 4 games)
--   slot 52 = SeraphinePassiveNotesMissileToAlly while it lasts (0.96)
BuffName = "seraphinepassiveechostage2"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphinePassiveNotesMissileToAlly", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphinePassiveNotesMissileOrbitingAlly", TargetVar = "Owner"}}
}
