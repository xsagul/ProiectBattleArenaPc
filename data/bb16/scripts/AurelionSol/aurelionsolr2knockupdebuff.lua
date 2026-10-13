-- aurelionsolr2knockupdebuff: written by tools/bb_write16.py from the replays (48 instances, 9 games)
--   given when aurelionsolrannouncement is spent (1.00)
--   given when aurelionsolrmanager is spent (1.00)
--   slot 52 = AurelionSolR2Shockwave while it lasts (1.00)
--   slot 52 = AurelionSolR2SFXMissile while it lasts (1.00)
--   slot 3 = AurelionSolR while it lasts (1.00)
BuffName = "aurelionsolr2knockupdebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "AurelionSolR2Shockwave", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "AurelionSolR2SFXMissile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "AurelionSolR", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
