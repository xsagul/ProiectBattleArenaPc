-- illaoievesselvo: written by tools/bb_write16.py from the replays (72 instances, 4 games)
--   given when IllaoiE is spent (1.00)
--   given when illaoiespirittimervisual is spent (0.92)
--   slot 48 = IllaoiESpiritMissile while it lasts (1.00)
BuffName = "illaoievesselvo"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "IllaoiESpiritMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
