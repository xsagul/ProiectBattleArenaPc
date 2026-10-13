-- katarinarsound: written by tools/bb_write16.py from the replays (172 instances, 14 games)
--   given by the cast of KatarinaR (0.95)
--   slot 45 = KatarinaRMis while it lasts (1.00)
BuffName = "katarinarsound"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "KatarinaRMis", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
