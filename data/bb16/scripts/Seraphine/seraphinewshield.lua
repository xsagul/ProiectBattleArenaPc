-- seraphinewshield: written by tools/bb_write16.py from the replays (447 instances, 4 games)
--   given by the cast of SeraphineW (0.99)
--   slot 52 = SeraphinePassiveNotesMissileToAlly while it lasts (1.00)
--   slot 48 = SeraphineWCast while it lasts (0.99)
BuffName = "seraphinewshield"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "SeraphinePassiveNotesMissileToAlly", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "SeraphineWCast", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
