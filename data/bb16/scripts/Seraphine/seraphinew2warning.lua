-- seraphinew2warning: written by tools/bb_write16.py from the replays (96 instances, 4 games)
--   slot 52 = SeraphinePassiveNotesMissileToAlly while it lasts (1.00)
BuffName = "seraphinew2warning"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphinePassiveNotesMissileToAlly", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphineW2HealMissile", TargetVar = "Owner"}}
}
