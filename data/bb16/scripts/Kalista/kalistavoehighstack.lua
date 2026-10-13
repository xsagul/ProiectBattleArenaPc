-- kalistavoehighstack: written by tools/bb_write16.py from the replays (59 instances, 10 games)
--   slot 45 = KalistaExpungeParticle while it lasts (1.00)
--   slot 45 = KalistaExpunge while it lasts (1.00)
BuffName = "kalistavoehighstack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "KalistaExpungeParticle", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "KalistaExpunge", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
